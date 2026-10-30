use http::{HeaderMap, HeaderValue, StatusCode, header};

use super::{guarded, request_id, secure};
use crate::response::Reply;

fn headers(pairs: &[(&'static str, &[u8])]) -> HeaderMap {
    let mut map = HeaderMap::new();
    for (name, value) in pairs {
        map.append(*name, HeaderValue::from_bytes(value).unwrap());
    }
    map
}

#[test]
fn the_request_id_keeps_the_last_token_cleaned_and_capped() {
    assert_eq!(
        request_id(&headers(&[("x-request-id", b"trace.id-01_A")])),
        "trace.id-01_A"
    );
    assert_eq!(
        request_id(&headers(&[("x-request-id", b"a b<c>d\xe9e!f/g")])),
        "abcdefg"
    );
    assert_eq!(
        request_id(&headers(&[
            ("x-request-id", b"first"),
            ("x-request-id", b"second")
        ])),
        "second"
    );
    assert_eq!(
        request_id(&headers(&[("x-request-id", &[b'r'; 300])])),
        "r".repeat(200)
    );
    for empty in [headers(&[]), headers(&[("x-request-id", b"<> \xe9")])] {
        let minted = request_id(&empty);
        assert_eq!(minted.len(), 32);
        assert!(
            minted
                .bytes()
                .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
        );
    }
}

fn names(response: &http::Response<http_body_util::Full<bytes::Bytes>>) -> Vec<(String, String)> {
    response
        .headers()
        .iter()
        .map(|(name, value)| (name.as_str().to_owned(), value.to_str().unwrap().to_owned()))
        .collect()
}

#[test]
fn every_reply_gets_the_security_headers_in_place_of_its_own() {
    let reply = Reply::json(
        StatusCode::OK,
        &b"{}"[..],
        vec![
            (
                header::X_FRAME_OPTIONS,
                HeaderValue::from_static("SAMEORIGIN"),
            ),
            (header::CACHE_CONTROL, HeaderValue::from_static("no-store")),
            (
                header::CONTENT_SECURITY_POLICY,
                HeaderValue::from_static("own"),
            ),
        ],
    );
    let response = secure(
        reply,
        "/api/health",
        "abc",
        &HeaderValue::from_static("page"),
    );
    assert_eq!(response.status(), StatusCode::OK);
    assert_eq!(
        names(&response),
        [
            ("cache-control".into(), "no-store".into()),
            ("content-length".into(), "2".into()),
            ("content-type".into(), "application/json".into()),
            (
                "strict-transport-security".into(),
                "max-age=31536000; includeSubDomains".into()
            ),
            ("content-security-policy".into(), "page".into()),
            ("x-content-type-options".into(), "nosniff".into()),
            ("x-frame-options".into(), "DENY".into()),
            (
                "referrer-policy".into(),
                "strict-origin-when-cross-origin".into()
            ),
            (
                "permissions-policy".into(),
                "camera=(), microphone=(), geolocation=(), payment=(), usb=()".into()
            ),
            ("x-request-id".into(), "abc".into()),
        ]
    );
}

#[test]
fn only_the_exact_oauth_paths_drop_the_referrer_and_only_the_callback_keeps_its_policy() {
    let own = || {
        Reply::new(
            StatusCode::OK,
            vec![(
                header::CONTENT_SECURITY_POLICY,
                HeaderValue::from_static("own"),
            )],
            None,
            &b""[..],
        )
    };
    let page = HeaderValue::from_static("page");
    let header =
        |response: &http::Response<_>, name| response.headers()[name].to_str().unwrap().to_owned();
    let callback = secure(own(), "/api/oauth/cloudflare/callback", "a", &page);
    assert_eq!(header(&callback, "content-security-policy"), "own");
    assert_eq!(header(&callback, "referrer-policy"), "no-referrer");
    let start = secure(own(), "/api/oauth/cloudflare/start", "a", &page);
    assert_eq!(header(&start, "content-security-policy"), "page");
    assert_eq!(header(&start, "referrer-policy"), "no-referrer");
    let bare = secure(
        Reply::new(StatusCode::OK, Vec::new(), None, &b""[..]),
        "/api/oauth/cloudflare/callback",
        "a",
        &page,
    );
    assert_eq!(header(&bare, "content-security-policy"), "page");
    let newline = secure(own(), "/api/oauth/cloudflare/start\n", "a", &page);
    assert_eq!(
        header(&newline, "referrer-policy"),
        "strict-origin-when-cross-origin"
    );
}

#[tokio::test]
async fn a_panicking_handler_answers_the_closed_500() {
    assert_eq!(
        guarded(
            "/x",
            Box::pin(async { Reply::new(StatusCode::OK, Vec::new(), None, &b""[..]) })
        )
        .await
        .status,
        StatusCode::OK
    );
    let failed = guarded("/x", Box::pin(async { panic!("PRIVATE_SENTINEL") })).await;
    assert_eq!(failed.status, StatusCode::INTERNAL_SERVER_ERROR);
    assert_eq!(failed.body, &b"{\"detail\":\"internal server error\"}"[..]);
}
