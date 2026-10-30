//! The bodies of the server-only broker operations: exact JSON objects posted by a Local Space, never by a browser.
//!
//! In order: any `Origin` header, or a first `Content-Type` other than exactly `application/json`, is 403; no
//! `Content-Length` is 411; a length past 32 KiB is 413 before anything is read; an unreadable length is 400; the body
//! is read within the bound; an empty body is `{}`; anything but a strict JSON object with exactly the operation's
//! member names is 400.

use bytes::Bytes;
use http::{HeaderMap, StatusCode, header};
use http_body_util::{BodyExt, combinators::UnsyncBoxBody};
use strict_json::Value;

/// The largest broker request body.
pub const MAX_BODY_BYTES: usize = 32 * 1024;

/// The error of a request body of any source.
pub type BodyError = Box<dyn std::error::Error + Send + Sync + 'static>;
/// A request body of any source.
pub type Body = UnsyncBoxBody<Bytes, BodyError>;

/// The members of an admitted body, or the status that refuses it.
///
/// # Errors
///
/// The status of the first rule the request breaks.
pub async fn admitted(
    headers: &HeaderMap,
    body: Body,
    fields: &[&str],
) -> Result<Vec<(String, Value)>, StatusCode> {
    let json = headers
        .get(header::CONTENT_TYPE)
        .is_some_and(|value| value == "application/json");
    if headers.contains_key(header::ORIGIN) || !json {
        return Err(StatusCode::FORBIDDEN);
    }
    let length = headers
        .get(header::CONTENT_LENGTH)
        .ok_or(StatusCode::LENGTH_REQUIRED)?;
    let length = length
        .to_str()
        .ok()
        .and_then(|length| length.parse::<usize>().ok())
        .ok_or(StatusCode::BAD_REQUEST)?;
    if length > MAX_BODY_BYTES {
        return Err(StatusCode::PAYLOAD_TOO_LARGE);
    }
    let bytes = bounded(body).await?;
    let document: &[u8] = if bytes.is_empty() { b"{}" } else { &bytes };
    match strict_json::parse(document) {
        Ok(Value::Object(members))
            if members.len() == fields.len()
                && fields
                    .iter()
                    .all(|field| members.iter().any(|(name, _)| name == field)) =>
        {
            Ok(members)
        }
        _ => Err(StatusCode::BAD_REQUEST),
    }
}

/// The body's data, refused once it passes the bound (413) or fails to arrive (400).
async fn bounded(mut body: Body) -> Result<Vec<u8>, StatusCode> {
    let mut bytes = Vec::new();
    while let Some(frame) = body.frame().await {
        let data = frame
            .or(Err(StatusCode::BAD_REQUEST))?
            .into_data()
            .unwrap_or_default();
        if bytes.len() + data.len() > MAX_BODY_BYTES {
            return Err(StatusCode::PAYLOAD_TOO_LARGE);
        }
        bytes.extend_from_slice(&data);
    }
    Ok(bytes)
}

/// The string value of member `name`.
#[must_use]
pub fn text<'a>(members: &'a [(String, Value)], name: &str) -> Option<&'a str> {
    members
        .iter()
        .find(|(key, _)| key == name)
        .and_then(|(_, value)| match value {
            Value::String(text) => Some(text.as_str()),
            _ => None,
        })
}

/// The value of member `name`.
#[must_use]
pub fn member<'a>(members: &'a [(String, Value)], name: &str) -> Option<&'a Value> {
    members
        .iter()
        .find(|(key, _)| key == name)
        .map(|(_, value)| value)
}

#[cfg(test)]
mod tests {
    use bytes::Bytes;
    use http::{HeaderMap, HeaderValue, StatusCode};
    use http_body_util::{BodyExt, Full, StreamBody};
    use strict_json::Value;

    use super::{Body, admitted, member, text};

    fn body(bytes: &'static [u8]) -> Body {
        Full::new(Bytes::from_static(bytes))
            .map_err(Into::into)
            .boxed_unsync()
    }

    fn headers(pairs: &[(&'static str, &str)]) -> HeaderMap {
        let mut headers = HeaderMap::new();
        for (name, value) in pairs {
            headers.append(*name, HeaderValue::from_str(value).unwrap());
        }
        headers
    }

    const JSON: (&str, &str) = ("content-type", "application/json");

    async fn status(
        pairs: &[(&'static str, &str)],
        bytes: &'static [u8],
    ) -> Result<usize, StatusCode> {
        admitted(&headers(pairs), body(bytes), &["a", "b"])
            .await
            .map(|members| members.len())
    }

    #[tokio::test]
    async fn read_admits_one_bounded_object_and_an_empty_body() {
        let length = ("content-length", "15");
        assert_eq!(
            status(&[JSON, length], b"{\"a\":1,\"b\":\"x\"}").await,
            Ok(2)
        );
        let members = admitted(&headers(&[JSON, ("content-length", "0")]), body(b""), &[])
            .await
            .unwrap();
        assert_eq!(members, Vec::new());
    }

    #[tokio::test]
    async fn browser_requests_and_other_media_types_are_forbidden() {
        for pairs in [
            &[JSON, ("origin", ""), ("content-length", "2")][..],
            &[
                ("content-type", "application/json; charset=utf-8"),
                ("content-length", "2"),
            ],
            &[
                ("content-type", "text/plain"),
                JSON,
                ("content-length", "2"),
            ],
            &[("content-length", "2")],
        ] {
            assert_eq!(
                status(pairs, b"{}").await,
                Err(StatusCode::FORBIDDEN),
                "{pairs:?}"
            );
        }
    }

    #[tokio::test]
    async fn oauth_body_requires_an_explicit_length() {
        assert_eq!(
            status(&[JSON], b"{}").await,
            Err(StatusCode::LENGTH_REQUIRED)
        );
    }

    #[tokio::test]
    async fn read_refuses_invalid_length_oversize_duplicate_keys_and_non_objects() {
        assert_eq!(
            status(&[JSON, ("content-length", "x")], b"{}").await,
            Err(StatusCode::BAD_REQUEST)
        );
        assert_eq!(
            status(&[JSON, ("content-length", "\u{e9}")], b"{}").await,
            Err(StatusCode::BAD_REQUEST)
        );
        assert_eq!(
            status(&[JSON, ("content-length", "32769")], b"{}").await,
            Err(StatusCode::PAYLOAD_TOO_LARGE)
        );
        exact_members_only().await;
    }

    async fn exact_members_only() {
        for bytes in [
            &b"{\"a\":1}"[..],
            b"{\"a\":1,\"c\":2}",
            b"{\"a\":1,\"b\":2,\"c\":3}",
            b"{\"a\":1,\"a\":2}",
            b"[]",
            b"{",
            b"",
        ] {
            assert_eq!(
                status(&[JSON, ("content-length", "1")], bytes).await,
                Err(StatusCode::BAD_REQUEST)
            );
        }
    }

    #[tokio::test]
    async fn an_unreadable_body_is_invalid() {
        let failing = StreamBody::new(futures_util::stream::iter([Err::<
            hyper::body::Frame<Bytes>,
            _,
        >(Box::<
            dyn std::error::Error + Send + Sync,
        >::from(
            "broken"
        ))]))
        .boxed_unsync();
        let refused = admitted(&headers(&[JSON, ("content-length", "2")]), failing, &[]).await;
        assert_eq!(refused.err(), Some(StatusCode::BAD_REQUEST));
        let long: &'static [u8] = Box::leak(vec![b' '; 32 * 1024 + 1].into_boxed_slice());
        let oversized = admitted(&headers(&[JSON, ("content-length", "2")]), body(long), &[]).await;
        assert_eq!(oversized.err(), Some(StatusCode::PAYLOAD_TOO_LARGE));
    }

    #[test]
    fn members_are_read_by_name_and_strings_by_type() {
        let members = vec![
            ("a".to_owned(), Value::String("x".to_owned())),
            ("b".to_owned(), Value::Null),
        ];
        assert_eq!(text(&members, "a"), Some("x"));
        assert_eq!(text(&members, "b"), None);
        assert_eq!(text(&members, "c"), None);
        assert_eq!(member(&members, "b"), Some(&Value::Null));
        assert_eq!(member(&members, "c"), None);
    }
}
