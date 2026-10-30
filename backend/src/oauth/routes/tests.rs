//! The broker routes, named after the Python route tests they replace, plus the owned-operation tests of the Rust
//! design.

use std::{
    net::{IpAddr, Ipv4Addr},
    sync::Arc,
    time::Duration,
};

use bytes::Bytes;
use http::{HeaderMap, HeaderValue, StatusCode};
use http_body_util::{BodyExt, Full};

use super::{Oauth, Post, exact_query};
use crate::{
    clock::ManualClock,
    oauth::{
        body::Body,
        broker::challenge_of,
        testing::{
            Fake, Recorded, broker, latest_authorization, neuron_answer, neuron_answer_for, reply,
        },
    },
    ratelimit::{StartLimit, trusted_proxies},
    response::Reply,
};

const VERIFIER: &str = "vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv";
const START: &str = "/api/oauth/cloudflare/start";
const CALLBACK: &str = "/api/oauth/cloudflare/callback";
const PEER: IpAddr = IpAddr::V4(Ipv4Addr::new(192, 0, 2, 10));
const SCOPES: &str = "dns.read+dns.write+offline_access+zone.read";

async fn routes_behind(
    proxies: &str,
    script: impl Fn(&Recorded) -> Vec<u8> + Send + Sync + 'static,
) -> (Fake, Arc<Oauth>) {
    let (fake, broker, _clock) = broker(script).await;
    let proxies = trusted_proxies(Some(std::ffi::OsStr::new(proxies))).unwrap();
    let limit = StartLimit::new(proxies, Arc::new(ManualClock::at(0)));
    (fake, Arc::new(Oauth::new(broker, limit)))
}

async fn routes(
    script: impl Fn(&Recorded) -> Vec<u8> + Send + Sync + 'static,
) -> (Fake, Arc<Oauth>) {
    routes_behind("10.0.0.0/32", script).await
}

fn start_query(state: &str, callback: &str) -> String {
    format!(
        "state={state}&code_challenge={}&scope={SCOPES}&callback={callback}",
        challenge_of(VERIFIER)
    )
}

async fn start(oauth: &Oauth, state: &str, callback: &str) -> Reply {
    oauth
        .start(
            PEER,
            &HeaderMap::new(),
            Some(&start_query(state, callback)),
            START,
        )
        .await
}

fn json_headers(length: usize) -> HeaderMap {
    let mut headers = HeaderMap::new();
    headers.insert("content-type", HeaderValue::from_static("application/json"));
    headers.insert("content-length", HeaderValue::from(length));
    headers
}

fn body(text: &str) -> Body {
    Full::new(Bytes::from(text.to_owned()))
        .map_err(Into::into)
        .boxed_unsync()
}

async fn post(oauth: &Oauth, operation: Post, text: &str) -> Reply {
    oauth
        .post(
            operation,
            &json_headers(text.len()),
            body(text),
            "/api/oauth/cloudflare/x",
        )
        .await
}

fn header<'a>(reply: &'a Reply, name: &str) -> Option<&'a str> {
    reply
        .headers
        .iter()
        .find(|(key, _)| key == name)
        .map(|(_, value)| value.to_str().unwrap())
}

fn callback_query(broker_state: &str, scopes: &str) -> String {
    format!("state={broker_state}&code=authorization-code-0001&scope={scopes}")
}

/// Start for `state` and run the callback; the callback's reply.
async fn called_back(fake: &Fake, oauth: &Oauth, state: &str, callback: &str) -> Reply {
    assert_eq!(
        start(oauth, state, callback).await.status,
        StatusCode::SEE_OTHER
    );
    let (broker_state, _) = latest_authorization(fake);
    oauth
        .callback(Some(&callback_query(&broker_state, SCOPES)), CALLBACK)
        .await
}

async fn wait_for(fake: &Fake, requests: usize) {
    while fake.received.lock().unwrap().len() < requests {
        tokio::time::sleep(Duration::from_millis(5)).await;
    }
}

#[tokio::test]
async fn browser_start_and_callback_redirect_without_oauth_tokens() {
    let (fake, oauth) = routes(neuron_answer).await;
    let started = start(&oauth, &"s".repeat(43), "loopback").await;
    assert_eq!(started.status, StatusCode::SEE_OTHER);
    let names: Vec<_> = started
        .headers
        .iter()
        .map(|(name, _)| name.as_str())
        .collect();
    assert_eq!(
        names,
        [
            "cache-control",
            "referrer-policy",
            "content-length",
            "location"
        ]
    );
    assert!(
        header(&started, "location")
            .unwrap()
            .starts_with("https://dash.cloudflare.com/oauth2/auth?")
    );
    assert_eq!(header(&started, "cache-control"), Some("private, no-store"));
    let (broker_state, _) = latest_authorization(&fake);
    let completed = oauth
        .callback(Some(&callback_query(&broker_state, SCOPES)), CALLBACK)
        .await;
    let location = header(&completed, "location").unwrap();
    assert!(location.starts_with("http://127.0.0.1:7777/api/oauth/cloudflare/callback?state=sss"));
    assert!(!location.contains("access-token") && !location.contains("refresh-token"));
    assert_eq!(header(&completed, "referrer-policy"), Some("no-referrer"));
    assert!(completed.body.is_empty());
}

#[tokio::test]
async fn browser_start_requires_an_explicit_callback_mode() {
    let (fake, oauth) = routes(neuron_answer).await;
    let query = start_query(&"s".repeat(43), "loopback").replace("&callback=loopback", "");
    let reply = oauth
        .start(PEER, &HeaderMap::new(), Some(&query), START)
        .await;
    assert_eq!(reply.status, StatusCode::BAD_REQUEST);
    assert!(fake.received.lock().unwrap().is_empty());
}

#[tokio::test]
async fn browser_callback_requires_the_closed_cloudflare_scope_envelope() {
    let (fake, oauth) = routes(neuron_answer).await;
    let state = "b".repeat(43);
    for query in [
        format!("state={state}&code=authorization-code-0001"),
        format!("{}&token=must-not-cross", callback_query(&state, SCOPES)),
        format!("state={state}&code=first&code=second&scope={SCOPES}"),
    ] {
        let reply = oauth.callback(Some(&query), CALLBACK).await;
        assert_eq!(reply.status, StatusCode::BAD_REQUEST, "{query}");
    }
    assert_eq!(
        oauth.callback(None, CALLBACK).await.status,
        StatusCode::BAD_REQUEST
    );
    assert!(fake.received.lock().unwrap().is_empty());
}

#[tokio::test]
async fn browser_routes_forward_the_canonical_read_only_scope_subset() {
    let (fake, oauth) = routes(neuron_answer).await;
    let read = "dns.read+offline_access+zone.read";
    let query = start_query(&"r".repeat(43), "loopback").replace(SCOPES, read);
    let started = oauth
        .start(PEER, &HeaderMap::new(), Some(&query), START)
        .await;
    assert!(
        header(&started, "location")
            .unwrap()
            .ends_with("scope=dns.read+offline_access+zone.read")
    );
    let (broker_state, _) = latest_authorization(&fake);
    let completed = oauth
        .callback(Some(&callback_query(&broker_state, read)), CALLBACK)
        .await;
    assert_eq!(completed.status, StatusCode::SEE_OTHER);
    let exchanged = fake.received.lock().unwrap().last().unwrap().body.clone();
    assert!(
        exchanged.ends_with("\"scopes\":[\"dns.read\",\"offline_access\",\"zone.read\"]}"),
        "{exchanged}"
    );
}

#[tokio::test]
async fn browser_start_forwards_only_the_named_local_domain_admin_callback() {
    let (fake, oauth) = routes(neuron_answer).await;
    let completed = called_back(&fake, &oauth, &"l".repeat(43), "local-domain").await;
    let location = header(&completed, "location").unwrap();
    assert!(
        location.starts_with("https://local.shimpz.com/api/oauth/cloudflare/callback?state=lll")
    );
}

#[tokio::test]
async fn out_of_band_callback_renders_only_a_hardened_completion_code() {
    let (fake, oauth) = routes(neuron_answer).await;
    let state = "o".repeat(43);
    let page = called_back(&fake, &oauth, &state, "out-of-band").await;
    assert_eq!(page.status, StatusCode::OK);
    assert_eq!(
        header(&page, "content-type"),
        Some("text/html; charset=utf-8")
    );
    assert_eq!(header(&page, "cache-control"), Some("private, no-store"));
    assert_eq!(
        header(&page, "cross-origin-opener-policy"),
        Some("same-origin")
    );
    assert_eq!(header(&page, "location"), None);
    let policy = header(&page, "content-security-policy").unwrap();
    let nonce = policy
        .split("'nonce-")
        .nth(1)
        .unwrap()
        .split('\'')
        .next()
        .unwrap();
    assert_eq!(nonce.len(), 24);
    let text = String::from_utf8(page.body.to_vec()).unwrap();
    assert!(text.contains(&format!("<script nonce=\"{nonce}\">")));
    assert!(text.contains(&format!("<style nonce=\"{nonce}\">")));
    assert!(text.contains(&format!("value=\"c1.{state}.")));
    assert!(!policy.contains("'unsafe-inline'") && !policy.contains("sha256-"));
    assert!(!text.contains("access-token") && !text.contains("refresh-token"));
}

#[tokio::test]
async fn browser_start_rejects_an_arbitrary_or_unknown_callback_before_the_broker() {
    let (fake, oauth) = routes(neuron_answer).await;
    for callback in ["https://evil.example", "remote"] {
        assert_eq!(
            start(&oauth, &"s".repeat(43), callback).await.status,
            StatusCode::BAD_REQUEST
        );
    }
    assert!(fake.received.lock().unwrap().is_empty());
}

/// Complete a loopback flow and claim it; the lease of the claimed tokens.
async fn claimed_lease(fake: &Fake, oauth: &Oauth) -> String {
    let state = "c".repeat(43);
    let completed = called_back(fake, oauth, &state, "loopback").await;
    let claim = header(&completed, "location")
        .unwrap()
        .rsplit("claim=")
        .next()
        .unwrap()
        .to_owned();
    let claimed = post(
        oauth,
        Post::Claim,
        &format!(
            "{{\"claim\":\"{claim}\",\"state\":\"{state}\",\"code_verifier\":\"{VERIFIER}\"}}"
        ),
    )
    .await;
    assert_eq!(claimed.status, StatusCode::OK);
    assert_eq!(header(&claimed, "cache-control"), Some("private, no-store"));
    let text = String::from_utf8(claimed.body.to_vec()).unwrap();
    let prefix = "{\"access_token\":\"access-token-0001\",\"refresh_token\":\"refresh-token-001\",\"expires_in\":3600,\
                  \"scopes\":[\"dns.read\",\"dns.write\",\"offline_access\",\"zone.read\"],\"broker_lease\":\"l3.";
    assert!(text.starts_with(prefix), "{text}");
    text.rsplit("\"broker_lease\":\"")
        .next()
        .unwrap()
        .trim_end_matches("\"}")
        .to_owned()
}

#[tokio::test]
async fn server_only_claim_refresh_and_revoke_are_exact_and_no_store() {
    let (fake, oauth) = routes(neuron_answer).await;
    let lease = claimed_lease(&fake, &oauth).await;
    let refreshed = post(
        &oauth,
        Post::Refresh,
        &format!(
            "{{\"refresh_token\":\"refresh-token-001\",\"broker_lease\":\"{lease}\",\
             \"scopes\":[\"dns.read\",\"dns.write\",\"offline_access\",\"zone.read\"]}}"
        ),
    )
    .await;
    assert_eq!(
        (refreshed.status, header(&refreshed, "cache-control")),
        (StatusCode::OK, Some("private, no-store"))
    );
    let revoked = post(
        &oauth,
        Post::Revoke,
        &format!("{{\"token\":\"access-token-0001\",\"broker_lease\":\"{lease}\"}}"),
    )
    .await;
    assert_eq!(
        (revoked.status, &revoked.body[..]),
        (StatusCode::OK, &b"{\"revoked\":true}"[..])
    );
}

#[tokio::test]
async fn token_routes_reject_browser_origin_duplicate_and_extra_fields() {
    let (fake, oauth) = routes(neuron_answer).await;
    let claim = format!(
        "{{\"claim\":\"{}\",\"state\":\"{}\",\"code_verifier\":\"{VERIFIER}\"}}",
        "a".repeat(64),
        "s".repeat(43)
    );
    let mut browser = json_headers(claim.len());
    browser.insert("origin", HeaderValue::from_static("https://evil.example"));
    let forbidden = oauth.post(Post::Claim, &browser, body(&claim), "/x").await;
    assert_eq!(forbidden.status, StatusCode::FORBIDDEN);
    let duplicate = claim.replacen("{\"claim\":", "{\"claim\":\"first\",\"claim\":", 1);
    assert_eq!(
        post(&oauth, Post::Claim, &duplicate).await.status,
        StatusCode::BAD_REQUEST
    );
    let extra = "{\"token\":\"private-token-123456\",\"broker_lease\":\"private-lease-123456\",\"extra\":true}";
    assert_eq!(
        post(&oauth, Post::Revoke, extra).await.status,
        StatusCode::BAD_REQUEST
    );
    assert!(fake.received.lock().unwrap().is_empty());
}

#[tokio::test]
async fn refresh_and_revoke_refuse_a_lease_expiry_with_non_ascii_digits() {
    let (fake, oauth) = routes(neuron_answer).await;
    let digest = "a".repeat(43);
    let lease = format!(
        "l3.{}.{}.{digest}.{digest}.{digest}.{digest}",
        "k".repeat(11),
        "\u{661}".repeat(10)
    );
    let refreshed = post(
        &oauth,
        Post::Refresh,
        &format!("{{\"refresh_token\":\"refresh-token-private-123456\",\"broker_lease\":\"{lease}\",\"scopes\":[\"dns.read\"]}}"),
    )
    .await;
    let revoked = post(
        &oauth,
        Post::Revoke,
        &format!("{{\"token\":\"access-token-private-123456\",\"broker_lease\":\"{lease}\"}}"),
    )
    .await;
    for reply in [&refreshed, &revoked] {
        assert_eq!(reply.status, StatusCode::BAD_GATEWAY);
        assert_eq!(
            &reply.body[..],
            b"{\"detail\":\"OAuth broker operation failed\"}"
        );
        assert_eq!(header(reply, "cache-control"), Some("private, no-store"));
    }
    assert!(fake.received.lock().unwrap().is_empty());
}

#[tokio::test]
async fn oauth_start_and_callback_translate_broker_failures() {
    let (_fake, oauth) = routes(|_| reply("502 Bad Gateway", "application/json", "{}")).await;
    assert_eq!(
        start(&oauth, &"f".repeat(43), "loopback").await.status,
        StatusCode::BAD_GATEWAY
    );
    let unknown = oauth
        .callback(Some(&callback_query(&"b".repeat(43), SCOPES)), CALLBACK)
        .await;
    assert_eq!(unknown.status, StatusCode::BAD_GATEWAY);
    let malformed = start(&oauth, "short", "loopback").await;
    assert_eq!(malformed.status, StatusCode::BAD_GATEWAY);
}

#[tokio::test]
async fn oauth_callback_rejects_an_unexpected_result() {
    // A callback completes only as a Local Admin redirect or the completion page; every other outcome is the 502.
    let (fake, oauth) = routes(|recorded| {
        if recorded.head.contains("/exchange ") {
            reply("200 OK", "application/json", "{\"unexpected\":true}")
        } else {
            neuron_answer(recorded)
        }
    })
    .await;
    let unexpected = called_back(&fake, &oauth, &"u".repeat(43), "loopback").await;
    assert_eq!(unexpected.status, StatusCode::BAD_GATEWAY);
}

#[tokio::test]
async fn oauth_start_limits_each_client_before_any_broker_work() {
    let (fake, oauth) = routes(neuron_answer).await;
    for index in 0..10 {
        assert_eq!(
            start(&oauth, &format!("{index:043}"), "loopback")
                .await
                .status,
            StatusCode::SEE_OTHER
        );
    }
    let refused = start(&oauth, &"x".repeat(43), "loopback").await;
    assert_eq!(refused.status, StatusCode::TOO_MANY_REQUESTS);
    assert_eq!(header(&refused, "retry-after"), Some("6"));
    assert_eq!(header(&refused, "cache-control"), Some("private, no-store"));
    assert_eq!(fake.received.lock().unwrap().len(), 10);
}

#[tokio::test]
async fn oauth_start_counts_malformed_starts_against_the_same_client() {
    let (fake, oauth) = routes(neuron_answer).await;
    for _ in 0..10 {
        let malformed = oauth.start(PEER, &HeaderMap::new(), None, START).await;
        assert_eq!(malformed.status, StatusCode::BAD_REQUEST);
    }
    assert_eq!(
        start(&oauth, &"s".repeat(43), "loopback").await.status,
        StatusCode::TOO_MANY_REQUESTS
    );
    assert!(fake.received.lock().unwrap().is_empty());
}

#[tokio::test]
async fn oauth_start_keys_a_direct_peer_by_its_socket_even_with_a_forged_client_header() {
    let (_fake, oauth) = routes(neuron_answer).await;
    let mut statuses = Vec::new();
    for attempt in 0..11 {
        let mut headers = HeaderMap::new();
        headers.insert(
            "cf-connecting-ip",
            HeaderValue::from_str(&format!("203.0.113.{attempt}")).unwrap(),
        );
        let query = start_query(&format!("{attempt:043}"), "loopback");
        statuses.push(
            oauth
                .start(PEER, &headers, Some(&query), START)
                .await
                .status
                .as_u16(),
        );
    }
    assert_eq!(statuses, [[303; 10].as_slice(), &[429]].concat());
}

#[tokio::test]
async fn oauth_start_keys_a_trusted_tunnel_peer_by_its_one_asserted_client() {
    let (fake, oauth) = routes_behind("10.202.84.0/24", neuron_answer).await;
    let tunnel = IpAddr::V4(Ipv4Addr::new(10, 202, 84, 2));
    let started = async |index: usize, clients: &[&str]| {
        let mut headers = HeaderMap::new();
        for client in clients {
            headers.append("cf-connecting-ip", HeaderValue::from_str(client).unwrap());
        }
        let query = start_query(&format!("{index:043}"), "loopback");
        oauth
            .start(tunnel, &headers, Some(&query), START)
            .await
            .status
            .as_u16()
    };
    let mut first = Vec::new();
    for index in 0..11 {
        first.push(started(index, &["203.0.113.5"]).await);
    }
    assert_eq!(first, [[303; 10].as_slice(), &[429]].concat());
    assert_eq!(started(20, &["203.0.113.6"]).await, 303);
    assert_eq!(started(21, &[]).await, 400);
    assert_eq!(started(22, &["203.0.113.7", "203.0.113.8"]).await, 400);
    assert_eq!(started(23, &["not-an-address"]).await, 400);
    assert_eq!(fake.received.lock().unwrap().len(), 11);
}

#[tokio::test]
async fn the_start_redirect_is_the_validated_consent_url_byte_for_byte() {
    let (_fake, oauth) =
        routes(|recorded| neuron_answer_for(recorded, "AZaz09_.~:/%2F?@[]!$'()*,;-")).await;
    let started = start(&oauth, &"s".repeat(43), "out-of-band").await;
    assert_eq!(started.status, StatusCode::SEE_OTHER);
    let location = header(&started, "location").unwrap();
    assert!(
        location.contains("&client_id=AZaz09_.~:/%2F?@[]!$'()*,;-&"),
        "{location}"
    );
}

#[tokio::test]
async fn server_only_operations_refuse_wrong_member_types_as_broker_failures() {
    let (_fake, oauth) = routes(neuron_answer).await;
    for (operation, text) in [
        (
            Post::Claim,
            "{\"claim\":1,\"state\":\"s\",\"code_verifier\":\"v\"}",
        ),
        (
            Post::Claim,
            "{\"claim\":\"c\",\"state\":1,\"code_verifier\":\"v\"}",
        ),
        (
            Post::Claim,
            "{\"claim\":\"c\",\"state\":\"s\",\"code_verifier\":1}",
        ),
        (
            Post::Refresh,
            "{\"refresh_token\":\"r\",\"broker_lease\":\"l\",\"scopes\":\"dns.read\"}",
        ),
        (
            Post::Refresh,
            "{\"refresh_token\":1,\"broker_lease\":\"l\",\"scopes\":[\"dns.read\"]}",
        ),
        (
            Post::Refresh,
            "{\"refresh_token\":\"r\",\"broker_lease\":1,\"scopes\":[\"dns.read\"]}",
        ),
        (Post::Revoke, "{\"token\":1,\"broker_lease\":\"l\"}"),
        (Post::Revoke, "{\"token\":\"t\",\"broker_lease\":1}"),
    ] {
        assert_eq!(
            post(&oauth, operation, text).await.status,
            StatusCode::BAD_GATEWAY,
            "{text}"
        );
    }
}

#[tokio::test]
async fn capacity_recovers_after_disconnected_operations_end() {
    let (fake, oauth) = routes(neuron_answer).await;
    fake.held.send_replace(true);
    for index in 0..16 {
        let oauth = Arc::clone(&oauth);
        let peer = IpAddr::V4(Ipv4Addr::new(192, 0, 2, index));
        let query = start_query(&format!("{index:043}"), "loopback");
        let waiting = tokio::spawn(async move {
            oauth
                .start(peer, &HeaderMap::new(), Some(&query), START)
                .await
        });
        tokio::time::sleep(Duration::from_millis(10)).await;
        waiting.abort();
    }
    let refused = oauth
        .callback(Some("state=x&code=y&scope=z"), CALLBACK)
        .await;
    assert_eq!(refused.status, StatusCode::TOO_MANY_REQUESTS);
    assert_eq!(header(&refused, "retry-after"), Some("1"));
    wait_for(&fake, 8).await;
    fake.held.send_replace(false);
    wait_for(&fake, 16).await;
    let recovered = tokio::time::timeout(Duration::from_secs(10), async {
        loop {
            let reply = oauth
                .callback(Some("state=x&code=y&scope=z"), CALLBACK)
                .await;
            if reply.status != StatusCode::TOO_MANY_REQUESTS {
                return reply;
            }
            tokio::time::sleep(Duration::from_millis(10)).await;
        }
    })
    .await
    .unwrap();
    assert_eq!(
        recovered.status,
        StatusCode::BAD_GATEWAY,
        "admitted again once the disconnected starts ended"
    );
}

#[tokio::test]
async fn a_disconnect_during_a_held_authorization_keeps_the_operation_and_its_outcome() {
    let (fake, oauth) = routes(neuron_answer).await;
    fake.held.send_replace(true);
    let state = "d".repeat(43);
    let waiting = tokio::spawn({
        let (oauth, query) = (Arc::clone(&oauth), start_query(&state, "loopback"));
        async move {
            oauth
                .start(PEER, &HeaderMap::new(), Some(&query), START)
                .await
        }
    });
    wait_for(&fake, 1).await;
    waiting.abort();
    fake.held.send_replace(false);
    let (broker_state, _) = latest_authorization(&fake);
    let completed = oauth
        .callback(Some(&callback_query(&broker_state, SCOPES)), CALLBACK)
        .await;
    assert_eq!(
        completed.status,
        StatusCode::SEE_OTHER,
        "the disconnected start stored its authorization"
    );
}

#[tokio::test]
async fn a_disconnect_during_a_held_exchange_stores_the_grant_and_frees_the_reservation() {
    let (fake, oauth) = routes(neuron_answer).await;
    let state = "e".repeat(43);
    start(&oauth, &state, "out-of-band").await;
    let (broker_state, _) = latest_authorization(&fake);
    fake.held.send_replace(true);
    let waiting = tokio::spawn({
        let (oauth, query) = (Arc::clone(&oauth), callback_query(&broker_state, SCOPES));
        async move { oauth.callback(Some(&query), CALLBACK).await }
    });
    wait_for(&fake, 2).await;
    waiting.abort();
    fake.held.send_replace(false);
    tokio::time::timeout(Duration::from_secs(10), oauth.drained())
        .await
        .unwrap();
    assert!(
        !oauth.idle(),
        "the grant is stored and holds its local state"
    );
    let again = start(&oauth, &state, "loopback").await;
    assert_eq!(
        again.status,
        StatusCode::TOO_MANY_REQUESTS,
        "a drained capacity admits nothing"
    );
}

#[tokio::test]
async fn a_failed_exchange_after_a_disconnect_releases_the_local_state() {
    let (fake, oauth) = routes(|recorded| {
        if recorded.head.contains("/exchange ") {
            reply("502 Bad Gateway", "application/json", "{}")
        } else {
            neuron_answer(recorded)
        }
    })
    .await;
    let state = "f".repeat(43);
    start(&oauth, &state, "loopback").await;
    let (broker_state, _) = latest_authorization(&fake);
    fake.held.send_replace(true);
    let waiting = tokio::spawn({
        let (oauth, query) = (Arc::clone(&oauth), callback_query(&broker_state, SCOPES));
        async move { oauth.callback(Some(&query), CALLBACK).await }
    });
    wait_for(&fake, 2).await;
    waiting.abort();
    fake.held.send_replace(false);
    tokio::time::timeout(Duration::from_secs(10), oauth.drained())
        .await
        .unwrap();
    assert!(
        oauth.idle(),
        "the failed exchange released the local state and the reservation"
    );
}

#[tokio::test]
async fn an_aborted_operation_restores_the_broker_and_a_panic_answers_500() {
    let (fake, oauth) = routes(neuron_answer).await;
    fake.held.send_replace(true);
    let state = "a".repeat(43);
    let waiting = tokio::spawn({
        let (oauth, query) = (Arc::clone(&oauth), start_query(&state, "loopback"));
        async move {
            oauth
                .start(PEER, &HeaderMap::new(), Some(&query), START)
                .await
        }
    });
    wait_for(&fake, 1).await;
    oauth.abort();
    assert_eq!(
        waiting.await.unwrap().status,
        StatusCode::INTERNAL_SERVER_ERROR
    );
    fake.held.send_replace(false);
    assert_eq!(
        start(&oauth, &state, "loopback").await.status,
        StatusCode::SEE_OTHER
    );
    let panicked = oauth
        .owned(
            "/x",
            Box::pin(async { panic!("an operation failed unexpectedly") }),
        )
        .await;
    assert_eq!(panicked.status, StatusCode::INTERNAL_SERVER_ERROR);
}

#[test]
fn an_exact_query_holds_each_name_once_and_nothing_else() {
    assert_eq!(
        exact_query(Some("b=2&a=1"), &["a", "b"]),
        Some(vec!["1".to_owned(), "2".to_owned()])
    );
    assert_eq!(exact_query(Some("a=1&b=2&a=3"), &["a", "b"]), None);
    assert_eq!(exact_query(Some("a=1&b=2&c"), &["a", "b"]), None);
    assert_eq!(exact_query(Some("a=1"), &["a", "b"]), None);
    assert_eq!(exact_query(None, &[]), Some(Vec::new()));
}
