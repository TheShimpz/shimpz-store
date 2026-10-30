use std::path::PathBuf;

use strict_json::Value;

use super::{Neuron, consent_url, json_media_type, tokens};
use crate::oauth::{
    BrokerError,
    shape::Scopes,
    testing::{Egress, Fake, fake, reply},
};

const STATE: &str = "SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS";
const CHALLENGE: &str = "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC";

fn scopes() -> Scopes {
    Scopes::sorted(&["dns.read", "zone.read"]).unwrap()
}

fn consent(query: &str) -> String {
    format!("https://dash.cloudflare.com/oauth2/auth?{query}")
}

fn good_query() -> String {
    format!(
        "response_type=code&client_id=client-1&redirect_uri=https://shimpz.com/api/oauth/cloudflare/callback\
         &state={STATE}&code_challenge={CHALLENGE}&code_challenge_method=S256&scope=dns.read+zone.read"
    )
}

fn neuron(fake: &Fake) -> Neuron {
    Neuron::new(fake.tunnel.clone(), fake.credential.clone())
}

async fn answering(body: &str) -> (Fake, Neuron) {
    let body = body.to_owned();
    let fake = fake(Egress::Established, "neuron.shimpz.com", move |_| {
        reply("200 OK", "application/json", &body)
    })
    .await;
    let client = neuron(&fake);
    (fake, client)
}

#[tokio::test]
async fn neuron_client_sends_access_service_identity_and_validates_fixed_authorization() {
    let url = consent(&good_query());
    let (fake, client) = answering(&format!("{{\"authorization_url\":\"{url}\"}}")).await;
    assert_eq!(
        client.authorization(STATE, CHALLENGE, &scopes()).await,
        Ok(url)
    );
    let received = fake.received.lock().unwrap()[0].clone();
    let body = format!(
        "{{\"state\":\"{STATE}\",\"code_challenge\":\"{CHALLENGE}\",\"scopes\":[\"dns.read\",\"zone.read\"]}}"
    );
    assert_eq!(received.body, body);
    let mut headers: Vec<&str> = received
        .head
        .lines()
        .skip(1)
        .filter(|line| !line.is_empty())
        .collect();
    headers.sort_unstable();
    let length = format!("content-length: {}", body.len());
    let secret = format!("cf-access-client-secret: {}", "s".repeat(32));
    let mut expected = vec![
        "accept-encoding: identity",
        "accept: application/json",
        "cf-access-client-id: client-id-0000000.access",
        secret.as_str(),
        "content-type: application/json",
        length.as_str(),
        "host: neuron.shimpz.com",
        "user-agent: shimpz-oauth-broker/1",
    ];
    expected.sort_unstable();
    assert_eq!(headers, expected);
    assert!(
        received
            .head
            .starts_with("POST /api/internal/oauth/cloudflare/authorization HTTP/1.1\r\n")
    );
}

#[tokio::test]
async fn neuron_authorization_rejects_invalid_response() {
    let url = consent(&good_query());
    for body in [
        format!("{{\"authorization_url\":\"{url}\",\"x\":1}}"),
        String::from("{\"authorization_url\":7}"),
        String::from("{\"url\":\"x\"}"),
        String::from("{}"),
    ] {
        let (_fake, client) = answering(&body).await;
        assert_eq!(
            client.authorization(STATE, CHALLENGE, &scopes()).await,
            Err(BrokerError),
            "{body}"
        );
    }
    let good = consent(&good_query());
    for url in [
        "https://dash.cloudflare.com/oauth2/auth?broken".to_owned(),
        good.replace("https://", "HTTPS://"),
        good.replace("dash.cloudflare.com", "dash.cloudflare.com:443"),
        good.replace("https://", "https://user@"),
        good.replace("oauth2/auth", "oauth2/./auth"),
        format!(" {good}"),
        format!("{good}&x=\u{e9}"),
        format!("{good}&x=\""),
    ] {
        assert_eq!(
            consent_url(&url, STATE, CHALLENGE, &scopes()),
            Err(BrokerError),
            "{url}"
        );
    }
}

#[test]
fn the_consent_url_has_the_exact_grammar_and_fields() {
    let good = good_query();
    assert_eq!(
        consent_url(&consent(&good), STATE, CHALLENGE, &scopes()),
        Ok(())
    );
    let long = consent(&format!("{good}&x={}", "x".repeat(4096)));
    let refused = [
        consent(&format!("{good}#f")),
        consent(&format!("{good}\t")),
        long,
        format!("https://DASH.cloudflare.com/oauth2/auth?{good}"),
        consent(&format!("{good}&")),
        consent(&format!("{good}&extra=1")),
        consent(&good.replace("response_type=code", "response_type=token")),
        consent(&good.replace("response_type=code", "state=x")),
        consent(&good.replace("https://shimpz.com", "https://evil.example")),
        consent(&good.replace(STATE, "other")),
        consent(&good.replace(CHALLENGE, "other")),
        consent(&good.replace("S256", "plain")),
        consent(&good.replace("dns.read+zone.read", "dns.read")),
        consent(&good.replace("client_id=client-1", "client_id=short")),
        consent(&good.replace("client_id=client-1", "client=client-1")),
        String::new(),
    ];
    for url in refused {
        assert_eq!(
            consent_url(&url, STATE, CHALLENGE, &scopes()),
            Err(BrokerError),
            "{url}"
        );
    }
}

#[tokio::test]
async fn neuron_exchange_refresh_and_revoke_validate_results() {
    let body = "{\"access_token\":\"aaaaaaaaaaaaaaaa\",\"refresh_token\":\"rrrrrrrrrrrrrrrr\",\
                \"scopes\":[\"dns.read\",\"zone.read\"],\"expires_in\":3600}";
    let (fake, client) = answering(body).await;
    let exchanged = client
        .exchange("code-0000000000000", "verifier", &scopes())
        .await
        .unwrap();
    assert_eq!(
        (
            exchanged.access.as_str(),
            exchanged.refresh.as_str(),
            exchanged.expires_in
        ),
        ("aaaaaaaaaaaaaaaa", "rrrrrrrrrrrrrrrr", 3600)
    );
    let refreshed = client.refresh("rrrrrrrrrrrrrrrr", &scopes()).await.unwrap();
    assert_eq!(refreshed.expires_in, 3600);
    let received = fake.received.lock().unwrap().clone();
    assert_eq!(
        received[0].body,
        "{\"code\":\"code-0000000000000\",\"code_verifier\":\"verifier\",\"scopes\":[\"dns.read\",\"zone.read\"]}"
    );
    assert!(
        received[0]
            .head
            .starts_with("POST /api/internal/oauth/cloudflare/exchange ")
    );
    assert_eq!(
        received[1].body,
        "{\"refresh_token\":\"rrrrrrrrrrrrrrrr\",\"scopes\":[\"dns.read\",\"zone.read\"]}"
    );
    assert!(
        received[1]
            .head
            .starts_with("POST /api/internal/oauth/cloudflare/refresh ")
    );
}

#[test]
fn neuron_tokens_reject_invalid_shape_scopes_and_expiry() {
    let parse = |text: &str| strict_json::parse(text.as_bytes()).unwrap();
    let good = "{\"access_token\":\"aaaaaaaaaaaaaaaa\",\"refresh_token\":\"rrrrrrrrrrrrrrrr\",\
                \"scopes\":[\"dns.read\",\"zone.read\"],\"expires_in\":30}";
    assert!(tokens(&parse(good), &scopes()).is_ok());
    let refused = [
        good.replace("\"expires_in\":30", "\"expires_in\":29"),
        good.replace("\"expires_in\":30", "\"expires_in\":31536001"),
        good.replace("\"expires_in\":30", "\"expires_in\":30.0"),
        good.replace("\"expires_in\":30", "\"expires_in\":true"),
        good.replace("aaaaaaaaaaaaaaaa", "short"),
        good.replace("rrrrrrrrrrrrrrrr", "short"),
        good.replace(
            "\"refresh_token\":\"rrrrrrrrrrrrrrrr\"",
            "\"refresh_token\":7",
        ),
        good.replace("[\"dns.read\",\"zone.read\"]", "[\"dns.read\"]"),
        good.replace(
            "[\"dns.read\",\"zone.read\"]",
            "[\"zone.read\",\"dns.read\"]",
        ),
        good.replace("\"scopes\"", "\"scope\""),
        good.replace('}', ",\"x\":1}"),
        String::from("[]"),
    ];
    for text in refused {
        assert!(tokens(&parse(&text), &scopes()).is_err(), "{text}");
    }
}

#[tokio::test]
async fn neuron_revoke_accepts_only_the_exact_acknowledgement() {
    let (fake, client) = answering("{\"revoked\":true}").await;
    assert_eq!(client.revoke("tttttttttttttttt").await, Ok(()));
    assert_eq!(
        fake.received.lock().unwrap()[0].body,
        "{\"token\":\"tttttttttttttttt\"}"
    );
    for body in [
        "{\"revoked\":1}",
        "{\"revoked\":1.0}",
        "{\"revoked\":\"true\"}",
        "{\"revoked\":false}",
        "{\"revoked\":null}",
        "{\"revoked\":true,\"x\":1}",
        "{}",
        "[true]",
    ] {
        let (_fake, client) = answering(body).await;
        assert_eq!(
            client.revoke("tttttttttttttttt").await,
            Err(BrokerError),
            "{body}"
        );
    }
}

#[tokio::test]
async fn neuron_object_rejects_status_json_and_shape() {
    let replies = [
        reply("502 Bad Gateway", "application/json", "{\"revoked\":true}"),
        reply("200 OK", "text/plain", "{\"revoked\":true}"),
        reply(
            "200 OK",
            "application/json",
            "{\"revoked\":true,\"revoked\":true}",
        ),
        reply(
            "200 OK",
            "application/json",
            &format!("{{\"revoked\":true,\"x\":\"{}\"}}", "x".repeat(32 * 1024)),
        ),
        b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 50\r\n\r\n{}"
            .to_vec(),
        b"garbage\r\n\r\n".to_vec(),
    ];
    for answer in replies {
        let fake = fake(Egress::Established, "neuron.shimpz.com", move |_| {
            answer.clone()
        })
        .await;
        assert_eq!(
            neuron(&fake).revoke("tttttttttttttttt").await,
            Err(BrokerError)
        );
    }
}

#[tokio::test]
async fn a_missing_credential_or_unreachable_egress_fails_before_any_request() {
    let (fake, _client) = answering("{\"revoked\":true}").await;
    let missing = Neuron::new(
        fake.tunnel.clone(),
        [PathBuf::from("/nonexistent/id"), fake.credential[1].clone()],
    );
    assert_eq!(missing.revoke("tttttttttttttttt").await, Err(BrokerError));
    assert!(fake.received.lock().unwrap().is_empty());
    let refused = fake_refusing().await;
    assert_eq!(
        neuron(&refused).revoke("tttttttttttttttt").await,
        Err(BrokerError)
    );
}

async fn fake_refusing() -> Fake {
    fake(
        Egress::Reply(b"HTTP/1.1 403 Forbidden\r\n\r\n"),
        "neuron.shimpz.com",
        |_| Vec::new(),
    )
    .await
}

#[test]
fn the_media_type_is_read_from_every_content_type_joined() {
    let headers = |values: &[&str]| {
        let mut map = http::HeaderMap::new();
        for value in values {
            map.append(http::header::CONTENT_TYPE, value.parse().unwrap());
        }
        map
    };
    assert!(json_media_type(&headers(&[
        " Application/JSON ; charset=utf-8"
    ])));
    assert!(!json_media_type(&headers(&[
        "application/json",
        "text/html"
    ])));
    assert!(!json_media_type(&headers(&[])));
    assert!(!json_media_type(&headers(&["application/json+x"])));
}

#[test]
fn production_reads_the_installed_access_credential() {
    let production = Neuron::production();
    assert_eq!(
        production.credential[0].to_str(),
        Some("/run/shimpz-store-oauth/access-client-id")
    );
    assert_eq!(
        production.credential[1].to_str(),
        Some("/run/shimpz-store-oauth/access-client-secret")
    );
}

#[tokio::test]
async fn neuron_client_rejects_world_readable_access_files() {
    let (fake, _client) = answering("{\"revoked\":true}").await;
    std::fs::set_permissions(
        &fake.credential[0],
        std::os::unix::fs::PermissionsExt::from_mode(0o444),
    )
    .unwrap();
    assert_eq!(
        neuron(&fake).revoke("tttttttttttttttt").await,
        Err(BrokerError)
    );
    assert!(fake.received.lock().unwrap().is_empty());
}

#[tokio::test]
async fn fixed_transport_rejects_endpoint_oversize_and_http_failure() {
    let oversized = format!("{{\"revoked\":true,\"x\":\"{}\"}}", "x".repeat(32 * 1024));
    let replies = [
        reply("200 OK", "application/json", &oversized),
        b"garbage\r\n\r\n".to_vec(),
        Vec::new(),
    ];
    for answer in replies {
        let fake = fake(Egress::Established, "neuron.shimpz.com", move |_| {
            answer.clone()
        })
        .await;
        assert_eq!(
            neuron(&fake).revoke("tttttttttttttttt").await,
            Err(BrokerError)
        );
        let path = fake.received.lock().unwrap()[0]
            .head
            .split(' ')
            .nth(1)
            .unwrap()
            .to_owned();
        assert_eq!(
            path, "/api/internal/oauth/cloudflare/revoke",
            "the endpoint is fixed"
        );
    }
}

#[test]
fn neuron_call_rejects_unknown_operation() {
    use super::Operation;
    let paths = [
        Operation::Authorization,
        Operation::Exchange,
        Operation::Refresh,
        Operation::Revoke,
    ]
    .map(Operation::path);
    assert_eq!(
        paths,
        [
            "/api/internal/oauth/cloudflare/authorization",
            "/api/internal/oauth/cloudflare/exchange",
            "/api/internal/oauth/cloudflare/refresh",
            "/api/internal/oauth/cloudflare/revoke",
        ],
        "the closed operation set has no other path"
    );
}

#[test]
fn neuron_authorization_admits_every_character_a_redirect_carries_unchanged() {
    let url = "https://dash.cloudflare.com/oauth2/auth?response_type=code&client_id=id_.~%3A%2F%2541%3F%3D%40%5B%5D%21%24%27%28%29%2A%2B%2C%3B-&redirect_uri=https%3A%2F%2Fshimpz.com%2Fapi%2Foauth%2Fcloudflare%2Fcallback&scope=dns.read+dns.write+offline_access+zone.read&state=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa&code_challenge=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb&code_challenge_method=S256";
    let all = Scopes::sorted(&["dns.read", "dns.write", "offline_access", "zone.read"]).unwrap();
    let reply = Value::Object(vec![(
        "authorization_url".to_owned(),
        Value::String(url.to_owned()),
    )]);
    assert_eq!(
        super::consent(&reply, &"a".repeat(43), &"b".repeat(43), &all),
        Ok(url.to_owned())
    );
}
