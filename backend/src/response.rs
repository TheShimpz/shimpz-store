//! The Store's replies before the security layer, each with the headers its Python response class wrote.
//!
//! A Starlette response writes the headers it is given, then `content-length`, then `content-type` when it has a
//! media type; a redirect adds `location` last. The security layer ([`crate::security`]) then drops the headers it
//! owns and appends its own.

use bytes::Bytes;
use http::{HeaderName, HeaderValue, StatusCode, header};

/// The JSON media type every API body uses.
pub const JSON: &str = "application/json";

/// One reply: its status, its own headers in order, and its body.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Reply {
    /// The status code.
    pub status: StatusCode,
    /// The reply's own headers, in the order they are written.
    pub headers: Vec<(HeaderName, HeaderValue)>,
    /// The body.
    pub body: Bytes,
}

impl Reply {
    /// A reply with the given headers, then its length, then its media type when it has one.
    #[must_use]
    pub fn new(
        status: StatusCode,
        mut headers: Vec<(HeaderName, HeaderValue)>,
        media_type: Option<&'static str>,
        body: impl Into<Bytes>,
    ) -> Self {
        let body = body.into();
        headers.push((header::CONTENT_LENGTH, HeaderValue::from(body.len())));
        if let Some(media_type) = media_type {
            headers.push((header::CONTENT_TYPE, HeaderValue::from_static(media_type)));
        }
        Self {
            status,
            headers,
            body,
        }
    }

    /// A JSON reply of already-encoded bytes.
    #[must_use]
    pub fn json(
        status: StatusCode,
        body: impl Into<Bytes>,
        headers: Vec<(HeaderName, HeaderValue)>,
    ) -> Self {
        Self::new(status, headers, Some(JSON), body)
    }

    /// `{"detail": <detail>}` for a detail of printable ASCII without quotes or backslashes.
    #[must_use]
    pub fn detail(
        status: StatusCode,
        detail: &str,
        headers: Vec<(HeaderName, HeaderValue)>,
    ) -> Self {
        Self::json(status, format!("{{\"detail\":\"{detail}\"}}"), headers)
    }

    /// An empty-bodied redirect to an already quoted location.
    #[must_use]
    pub fn redirect(
        status: StatusCode,
        location: HeaderValue,
        headers: Vec<(HeaderName, HeaderValue)>,
    ) -> Self {
        let mut reply = Self::new(status, headers, None, Bytes::new());
        reply.headers.push((header::LOCATION, location));
        reply
    }

    /// The reply's first value of `name`.
    #[must_use]
    pub fn header(&self, name: &HeaderName) -> Option<&HeaderValue> {
        self.headers
            .iter()
            .find(|(key, _)| key == name)
            .map(|(_, value)| value)
    }
}

/// `405 {"detail":"Method Not Allowed"}` naming the route's methods.
#[must_use]
pub fn not_allowed(allow: &'static str) -> Reply {
    Reply::detail(
        StatusCode::METHOD_NOT_ALLOWED,
        "Method Not Allowed",
        vec![(header::ALLOW, HeaderValue::from_static(allow))],
    )
}

/// The framework's `404 {"detail":"Not Found"}` for a path no route matches.
#[must_use]
pub fn not_found() -> Reply {
    Reply::detail(StatusCode::NOT_FOUND, "Not Found", Vec::new())
}

#[cfg(test)]
mod tests {
    use http::{HeaderValue, StatusCode, header};

    use super::{Reply, not_allowed, not_found};

    fn names(reply: &Reply) -> Vec<&str> {
        reply
            .headers
            .iter()
            .map(|(name, _)| name.as_str())
            .collect()
    }

    #[test]
    fn a_reply_writes_its_headers_then_its_length_then_its_type() {
        let reply = Reply::json(
            StatusCode::OK,
            &b"{}"[..],
            vec![(header::CACHE_CONTROL, HeaderValue::from_static("no-store"))],
        );
        assert_eq!(
            names(&reply),
            ["cache-control", "content-length", "content-type"]
        );
        assert_eq!(
            reply.header(&header::CONTENT_LENGTH),
            Some(&HeaderValue::from(2))
        );
        assert_eq!(reply.header(&header::ETAG), None);
    }

    #[test]
    fn a_redirect_has_no_media_type_and_names_its_location_last() {
        let reply = Reply::redirect(
            StatusCode::PERMANENT_REDIRECT,
            HeaderValue::from_static("/en"),
            Vec::new(),
        );
        assert_eq!(names(&reply), ["content-length", "location"]);
        assert!(reply.body.is_empty());
    }

    #[test]
    fn refusals_carry_the_framework_bodies() {
        let refused = not_allowed("POST");
        assert_eq!(refused.status, StatusCode::METHOD_NOT_ALLOWED);
        assert_eq!(refused.body, &b"{\"detail\":\"Method Not Allowed\"}"[..]);
        assert_eq!(
            refused.header(&header::ALLOW),
            Some(&HeaderValue::from_static("POST"))
        );
        assert_eq!(not_found().body, &b"{\"detail\":\"Not Found\"}"[..]);
    }
}
