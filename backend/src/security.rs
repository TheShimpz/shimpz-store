//! The security layer every reply leaves through: the browser security headers, the request id, and the 500 that
//! answers a panic.
//!
//! The layer drops any header it owns from the reply, then appends `strict-transport-security`, the page policy (or,
//! on the OAuth callback path, the policy the reply set itself), `x-content-type-options`, `x-frame-options`,
//! `referrer-policy` (`no-referrer` on the OAuth start and callback paths), `permissions-policy`, and the request id.

use std::{future::Future, panic::AssertUnwindSafe, pin::Pin};

use bytes::Bytes;
use futures_util::FutureExt;
use http::{HeaderMap, HeaderName, HeaderValue, Response, StatusCode, header};
use http_body_util::Full;

use crate::{
    response::Reply,
    route::{OAUTH_CALLBACK_PATH, OAUTH_START_PATH},
};

const REQUEST_ID: HeaderName = HeaderName::from_static("x-request-id");
const PERMISSIONS_POLICY: HeaderName = HeaderName::from_static("permissions-policy");
const OWNED: [HeaderName; 7] = [
    header::STRICT_TRANSPORT_SECURITY,
    header::X_CONTENT_TYPE_OPTIONS,
    header::REFERRER_POLICY,
    PERMISSIONS_POLICY,
    header::CONTENT_SECURITY_POLICY,
    header::X_FRAME_OPTIONS,
    REQUEST_ID,
];
/// The most characters of a caller's request id the Store keeps.
const MAX_REQUEST_ID_CHARS: usize = 200;

/// The request id of one request: the last `X-Request-ID` it carried, read as Latin-1, with every character outside
/// `[A-Za-z0-9._-]` removed and cut to 200 characters; a fresh random id when nothing is left.
#[must_use]
pub fn request_id(headers: &HeaderMap) -> String {
    let kept: String = headers
        .get_all(REQUEST_ID)
        .iter()
        .next_back()
        .map(HeaderValue::as_bytes)
        .unwrap_or_default()
        .iter()
        .map(|byte| char::from(*byte))
        .filter(|character| {
            character.is_ascii_alphanumeric() || matches!(character, '.' | '_' | '-')
        })
        .take(MAX_REQUEST_ID_CHARS)
        .collect();
    if kept.is_empty() {
        uuid::Uuid::new_v4().simple().to_string()
    } else {
        kept
    }
}

/// The reply a request's handler produced, or the closed 500 when it panicked.
pub async fn guarded(
    path: &str,
    handler: Pin<Box<dyn Future<Output = Reply> + Send + '_>>,
) -> Reply {
    AssertUnwindSafe(handler)
        .catch_unwind()
        .await
        .unwrap_or_else(|_| internal_error(path))
}

/// The closed 500 for a request whose handling failed unexpectedly, logged with its decoded path.
#[must_use]
pub fn internal_error(path: &str) -> Reply {
    crate::log::event(
        crate::log::Level::Error,
        "unhandled_exception",
        &[("path", path)],
    );
    Reply::detail(
        StatusCode::INTERNAL_SERVER_ERROR,
        "internal server error",
        Vec::new(),
    )
}

/// The response a reply becomes after the security layer, for the request with this decoded path and id.
///
/// # Panics
///
/// Never: every header name and value the layer writes is valid, and so is a reply's status.
#[must_use]
pub fn secure(
    reply: Reply,
    path: &str,
    request_id: &str,
    page_policy: &HeaderValue,
) -> Response<Full<Bytes>> {
    let own_policy = reply.header(&header::CONTENT_SECURITY_POLICY).cloned();
    let policy = match own_policy {
        Some(policy) if path == OAUTH_CALLBACK_PATH => policy,
        _ => page_policy.clone(),
    };
    let referrer = if path == OAUTH_START_PATH || path == OAUTH_CALLBACK_PATH {
        "no-referrer"
    } else {
        "strict-origin-when-cross-origin"
    };
    let mut response = Response::new(Full::new(reply.body));
    *response.status_mut() = reply.status;
    let headers = response.headers_mut();
    for (name, value) in reply.headers {
        if !OWNED.contains(&name) {
            headers.append(name, value);
        }
    }
    let layer = [
        (
            header::STRICT_TRANSPORT_SECURITY,
            HeaderValue::from_static("max-age=31536000; includeSubDomains"),
        ),
        (header::CONTENT_SECURITY_POLICY, policy),
        (
            header::X_CONTENT_TYPE_OPTIONS,
            HeaderValue::from_static("nosniff"),
        ),
        (header::X_FRAME_OPTIONS, HeaderValue::from_static("DENY")),
        (header::REFERRER_POLICY, HeaderValue::from_static(referrer)),
        (
            PERMISSIONS_POLICY,
            HeaderValue::from_static(
                "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
            ),
        ),
    ];
    for (name, value) in layer {
        headers.append(name, value);
    }
    let id = HeaderValue::from_str(request_id).expect("a request id holds only token characters");
    headers.append(REQUEST_ID, id);
    response
}

#[cfg(test)]
mod tests;
