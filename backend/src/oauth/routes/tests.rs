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
        testing::{Fake, broker, latest_authorization, neuron_answer, reply},
    },
    ratelimit::StartLimit,
    response::Reply,
};

const VERIFIER: &str = "vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv";
const START: &str = "/api/oauth/cloudflare/start";
const PEER: IpAddr = IpAddr::V4(Ipv4Addr::new(192, 0, 2, 1));

async fn routes(
    script: impl Fn(&crate::oauth::testing::Recorded) -> Vec<u8> + Send + Sync + 'static,
) -> (Fake, Arc<Oauth>) {
    let (fake, broker, _clock) = broker(script).await;
    let limit = StartLimit::new(Vec::new(), Arc::new(ManualClock::at(0)));
    (fake, Arc::new(Oauth::new(broker, limit)))
}

fn start_query(state: &str, callback: &str) -> String {
    format!(
        "state={state}&code_challenge={}&scope=dns.read+zone.read&callback={callback}",
        challenge_of(VERIFIER)
    )
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

/// Start for `state` and run the callback; the callback's reply.
async fn called_back(fake: &Fake, oauth: &Oauth, state: &str, callback: &str) -> Reply {
    let started = oauth
        .start(
            PEER,
            &HeaderMap::new(),
            Some(&start_query(state, callback)),
            START,
        )
        .await;
    assert_eq!(started.status, StatusCode::SEE_OTHER);
    let (broker_state, _) = latest_authorization(fake);
    let query = format!("state={broker_state}&code=code-0000000000000&scope=zone.read+dns.read");
    oauth
        .callback(Some(&query), "/api/oauth/cloudflare/callback")
        .await
}

#[tokio::test]
async fn a_start_redirects_to_the_consent_url_without_caching_or_a_referrer() {
    let (_fake, oauth) = routes(neuron_answer).await;
    let reply = oauth
        .start(
            PEER,
            &HeaderMap::new(),
            Some(&start_query(&"s".repeat(43), "loopback")),
            START,
        )
        .await;
    assert_eq!(reply.status, StatusCode::SEE_OTHER);
    let names: Vec<_> = reply
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
        header(&reply, "location")
            .unwrap()
            .starts_with("https://dash.cloudflare.com/oauth2/auth?")
    );
    assert_eq!(header(&reply, "cache-control"), Some("private, no-store"));
    assert!(reply.body.is_empty());
}

#[tokio::test]
async fn a_start_refuses_an_inexact_query_or_an_unknown_callback_before_the_broker() {
    let (fake, oauth) = routes(neuron_answer).await;
    let good = start_query(&"s".repeat(43), "loopback");
    for query in [
        None,
        Some(good.replace("&callback=loopback", "")),
        Some(format!("{good}&callback=loopback")),
        Some(format!("{good}&extra=1")),
        Some(good.replace("loopback", "remote")),
        Some(good.replace("loopback", "https://evil.example")),
    ] {
        let reply = oauth
            .start(PEER, &HeaderMap::new(), query.as_deref(), START)
            .await;
        assert_eq!(reply.status, StatusCode::BAD_REQUEST, "{query:?}");
    }
    assert!(fake.received.lock().unwrap().is_empty());
    let broken = oauth
        .start(
            PEER,
            &HeaderMap::new(),
            Some(&good.replace(&"s".repeat(43), "short")),
            START,
        )
        .await;
    assert_eq!(broken.status, StatusCode::BAD_GATEWAY);
}

#[tokio::test]
async fn the_eleventh_start_in_a_minute_is_limited_even_when_malformed() {
    let (_fake, oauth) = routes(neuron_answer).await;
    for _ in 0..10 {
        let reply = oauth.start(PEER, &HeaderMap::new(), None, START).await;
        assert_eq!(reply.status, StatusCode::BAD_REQUEST);
    }
    let limited = oauth.start(PEER, &HeaderMap::new(), None, START).await;
    assert_eq!(limited.status, StatusCode::TOO_MANY_REQUESTS);
    assert_eq!(header(&limited, "retry-after"), Some("6"));
}

#[tokio::test]
async fn a_callback_redirects_or_renders_the_completion_page_and_refuses_inexact_queries() {
    let (fake, oauth) = routes(neuron_answer).await;
    let redirected = called_back(&fake, &oauth, &"r".repeat(43), "loopback").await;
    assert_eq!(redirected.status, StatusCode::SEE_OTHER);
    assert!(
        header(&redirected, "location")
            .unwrap()
            .starts_with("http://127.0.0.1:7777/")
    );
    let page = called_back(&fake, &oauth, &"o".repeat(43), "out-of-band").await;
    assert_eq!(page.status, StatusCode::OK);
    assert_eq!(
        header(&page, "content-type"),
        Some("text/html; charset=utf-8")
    );
    for query in [
        None,
        Some("state=x&code=y"),
        Some("state=x&code=y&scope=z&scope=z"),
    ] {
        let reply = oauth
            .callback(query, "/api/oauth/cloudflare/callback")
            .await;
        assert_eq!(reply.status, StatusCode::BAD_REQUEST, "{query:?}");
    }
    let unknown = oauth
        .callback(
            Some("state=x&code=code-0000000000000&scope=dns.read"),
            "/api/oauth/cloudflare/callback",
        )
        .await;
    assert_eq!(unknown.status, StatusCode::BAD_GATEWAY);
}

#[tokio::test]
async fn claim_refresh_and_revoke_answer_exact_uncached_json() {
    let (fake, oauth) = routes(neuron_answer).await;
    let state = "c".repeat(43);
    let redirected = called_back(&fake, &oauth, &state, "loopback").await;
    let claim = header(&redirected, "location")
        .unwrap()
        .rsplit("claim=")
        .next()
        .unwrap()
        .to_owned();
    let claimed = post(
        &oauth,
        Post::Claim,
        &format!(
            "{{\"claim\":\"{claim}\",\"state\":\"{state}\",\"code_verifier\":\"{VERIFIER}\"}}"
        ),
    )
    .await;
    assert_eq!(claimed.status, StatusCode::OK);
    assert_eq!(header(&claimed, "cache-control"), Some("private, no-store"));
    let text = String::from_utf8(claimed.body.to_vec()).unwrap();
    let prefix = "{\"access_token\":\"access-token-0001\",\"refresh_token\":\"refresh-token-001\",\
                  \"expires_in\":3600,\"scopes\":[\"dns.read\",\"zone.read\"],\"broker_lease\":\"l3.";
    assert!(text.starts_with(prefix), "{text}");
    let lease = text
        .rsplit("\"broker_lease\":\"")
        .next()
        .unwrap()
        .trim_end_matches("\"}")
        .to_owned();
    let refreshed = post(
        &oauth,
        Post::Refresh,
        &format!("{{\"refresh_token\":\"refresh-token-001\",\"broker_lease\":\"{lease}\",\"scopes\":[\"dns.read\",\"zone.read\"]}}"),
    )
    .await;
    assert_eq!(refreshed.status, StatusCode::OK);
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
async fn server_only_operations_refuse_their_body_or_wrong_types() {
    let (_fake, oauth) = routes(neuron_answer).await;
    let mut browser = json_headers(2);
    browser.insert("origin", HeaderValue::from_static("https://shimpz.com"));
    let forbidden = oauth.post(Post::Revoke, &browser, body("{}"), "/x").await;
    assert_eq!(forbidden.status, StatusCode::FORBIDDEN);
    let inexact = post(&oauth, Post::Revoke, "{\"token\":\"x\"}").await;
    assert_eq!(inexact.status, StatusCode::BAD_REQUEST);
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
        (
            Post::Refresh,
            "{\"refresh_token\":\"refresh-token-001\",\"broker_lease\":\"l3.x\",\"scopes\":[\"dns.read\"]}",
        ),
        (Post::Revoke, "{\"token\":1,\"broker_lease\":\"l\"}"),
        (Post::Revoke, "{\"token\":\"t\",\"broker_lease\":1}"),
        (
            Post::Revoke,
            "{\"token\":\"access-token-0001\",\"broker_lease\":\"l3.x\"}",
        ),
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
        let state = format!("{index:043}");
        let peer = IpAddr::V4(Ipv4Addr::new(192, 0, 2, index));
        let waiting = tokio::spawn(async move {
            oauth
                .start(
                    peer,
                    &HeaderMap::new(),
                    Some(&start_query(&state, "loopback")),
                    START,
                )
                .await
        });
        tokio::time::sleep(Duration::from_millis(10)).await;
        waiting.abort();
    }
    let refused = oauth
        .callback(
            Some("state=x&code=y&scope=z"),
            "/api/oauth/cloudflare/callback",
        )
        .await;
    assert_eq!(refused.status, StatusCode::TOO_MANY_REQUESTS);
    assert_eq!(header(&refused, "retry-after"), Some("1"));
    while fake.received.lock().unwrap().len() < 8 {
        tokio::time::sleep(Duration::from_millis(10)).await;
    }
    fake.held.send_replace(false);
    tokio::time::timeout(Duration::from_secs(10), oauth.drained())
        .await
        .unwrap();
    assert_eq!(
        fake.received.lock().unwrap().len(),
        16,
        "every disconnected start reached Neuron"
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
    while fake.received.lock().unwrap().is_empty() {
        tokio::time::sleep(Duration::from_millis(5)).await;
    }
    waiting.abort();
    fake.held.send_replace(false);
    let (broker_state, _) = latest_authorization(&fake);
    let query = format!("state={broker_state}&code=code-0000000000000&scope=dns.read+zone.read");
    let completed = oauth
        .callback(Some(&query), "/api/oauth/cloudflare/callback")
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
    oauth
        .start(
            PEER,
            &HeaderMap::new(),
            Some(&start_query(&state, "out-of-band")),
            START,
        )
        .await;
    let (broker_state, _) = latest_authorization(&fake);
    fake.held.send_replace(true);
    let waiting = tokio::spawn({
        let (oauth, query) = (
            Arc::clone(&oauth),
            format!("state={broker_state}&code=code-0000000000000&scope=dns.read+zone.read"),
        );
        async move {
            oauth
                .callback(Some(&query), "/api/oauth/cloudflare/callback")
                .await
        }
    });
    while fake.received.lock().unwrap().len() < 2 {
        tokio::time::sleep(Duration::from_millis(5)).await;
    }
    waiting.abort();
    fake.held.send_replace(false);
    tokio::time::timeout(Duration::from_secs(10), oauth.drained())
        .await
        .unwrap();
    let again = oauth
        .start(
            PEER,
            &HeaderMap::new(),
            Some(&start_query(&state, "loopback")),
            START,
        )
        .await;
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
    oauth
        .start(
            PEER,
            &HeaderMap::new(),
            Some(&start_query(&state, "loopback")),
            START,
        )
        .await;
    let (broker_state, _) = latest_authorization(&fake);
    fake.held.send_replace(true);
    let waiting = tokio::spawn({
        let (oauth, query) = (
            Arc::clone(&oauth),
            format!("state={broker_state}&code=code-0000000000000&scope=dns.read+zone.read"),
        );
        async move {
            oauth
                .callback(Some(&query), "/api/oauth/cloudflare/callback")
                .await
        }
    });
    while fake.received.lock().unwrap().len() < 2 {
        tokio::time::sleep(Duration::from_millis(5)).await;
    }
    waiting.abort();
    fake.held.send_replace(false);
    tokio::time::sleep(Duration::from_millis(200)).await;
    let again = oauth
        .start(
            PEER,
            &HeaderMap::new(),
            Some(&start_query(&state, "loopback")),
            START,
        )
        .await;
    assert_eq!(
        again.status,
        StatusCode::SEE_OTHER,
        "the failed exchange released the local state"
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
    while fake.received.lock().unwrap().is_empty() {
        tokio::time::sleep(Duration::from_millis(5)).await;
    }
    oauth.abort();
    assert_eq!(
        waiting.await.unwrap().status,
        StatusCode::INTERNAL_SERVER_ERROR
    );
    fake.held.send_replace(false);
    let again = oauth
        .start(
            PEER,
            &HeaderMap::new(),
            Some(&start_query(&state, "loopback")),
            START,
        )
        .await;
    assert_eq!(again.status, StatusCode::SEE_OTHER);
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
