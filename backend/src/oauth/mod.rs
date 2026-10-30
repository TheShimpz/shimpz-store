//! The Cloudflare OAuth broker: its routes' shared refusal, and the capacity every broker operation runs within.

pub mod admission;
pub mod body;
pub mod broker;
pub mod completion;
pub mod lease;
pub mod neuron;
pub mod routes;
pub mod secret;
pub mod shape;
#[cfg(test)]
pub(crate) mod testing;
pub mod tunnel;

use http::{HeaderName, HeaderValue, StatusCode, header};

use crate::{log, response::Reply};

/// A broker operation failed; it carries nothing, so no private value can reach a reply or a log.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct BrokerError;

/// The cache policy of every broker reply: never stored.
pub const PRIVATE_NO_STORE: HeaderValue = HeaderValue::from_static("private, no-store");

/// The closed refusal of one broker operation, logged by its name only.
#[must_use]
pub fn failure(
    operation: &str,
    status: StatusCode,
    extra: Option<(HeaderName, HeaderValue)>,
) -> Reply {
    log::event(
        log::Level::Warning,
        "oauth_broker_rejected",
        &[("operation", operation)],
    );
    let mut headers = vec![(header::CACHE_CONTROL, PRIVATE_NO_STORE)];
    headers.extend(extra);
    Reply::detail(status, "OAuth broker operation failed", headers)
}

#[cfg(test)]
mod tests {
    use http::{HeaderValue, StatusCode, header};

    use super::failure;

    #[test]
    fn a_failure_is_a_closed_uncached_detail_with_any_extra_header_before_its_length() {
        let reply = failure("start", StatusCode::BAD_REQUEST, None);
        assert_eq!(reply.status, StatusCode::BAD_REQUEST);
        assert_eq!(
            &reply.body[..],
            b"{\"detail\":\"OAuth broker operation failed\"}"
        );
        let limited = failure(
            "start",
            StatusCode::TOO_MANY_REQUESTS,
            Some((header::RETRY_AFTER, HeaderValue::from(6_u64))),
        );
        let names: Vec<_> = limited
            .headers
            .iter()
            .map(|(name, _)| name.as_str())
            .collect();
        assert_eq!(
            names,
            [
                "cache-control",
                "retry-after",
                "content-length",
                "content-type"
            ]
        );
        assert_eq!(limited.headers[0].1, "private, no-store");
        assert_eq!(limited.headers[1].1, "6");
    }
}
