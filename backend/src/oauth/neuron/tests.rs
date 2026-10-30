use std::path::PathBuf;

use strict_json::Value;

use super::{Neuron, consent_url, json_media_type, only, tokens};
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
async fn authorization_posts_the_exact_request_and_returns_the_consent_url() {
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
async fn an_authorization_reply_with_another_member_or_a_non_string_url_fails() {
    let url = consent(&good_query());
    for body in [
        format!("{{\"authorization_url\":\"{url}\",\"x\":1}}"),
        String::from("{\"authorization_url\":7}"),
        String::from("{\"url\":\"x\"}"),
    ] {
        let (_fake, client) = answering(&body).await;
        assert_eq!(
            client.authorization(STATE, CHALLENGE, &scopes()).await,
            Err(BrokerError),
            "{body}"
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
async fn exchange_and_refresh_return_exactly_shaped_tokens_for_the_expected_scopes() {
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
fn tokens_need_every_member_in_shape() {
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
async fn revoke_needs_exactly_the_boolean_true_acknowledgement() {
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
async fn a_reply_that_is_not_a_json_object_from_a_200_json_response_fails() {
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
fn only_reads_a_single_member_object() {
    let object = |members: &[(&str, Value)]| {
        Value::Object(
            members
                .iter()
                .map(|(name, value)| ((*name).to_owned(), value.clone()))
                .collect(),
        )
    };
    assert_eq!(
        only(&object(&[("a", Value::Null)]), "a"),
        Some(&Value::Null)
    );
    assert_eq!(only(&object(&[("b", Value::Null)]), "a"), None);
    assert_eq!(
        only(&object(&[("a", Value::Null), ("b", Value::Null)]), "a"),
        None
    );
    assert_eq!(only(&Value::Null, "a"), None);
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
