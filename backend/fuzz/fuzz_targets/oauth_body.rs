//! Fuzzes the server-only broker body admission over arbitrary bytes: it must admit an exact object or refuse.
#![no_main]

use bytes::Bytes;
use http::{HeaderMap, HeaderValue};
use http_body_util::{BodyExt, Full};

libfuzzer_sys::fuzz_target!(|data: &[u8]| {
    let mut headers = HeaderMap::new();
    headers.insert("content-type", HeaderValue::from_static("application/json"));
    headers.insert("content-length", HeaderValue::from(data.len()));
    let body = Full::new(Bytes::copy_from_slice(data))
        .map_err(Into::into)
        .boxed_unsync();
    let runtime = tokio::runtime::Builder::new_current_thread()
        .build()
        .unwrap();
    let fields = ["refresh_token", "broker_lease", "scopes"];
    let _ = runtime.block_on(store_backend::oauth::body::admitted(
        &headers, body, &fields,
    ));
});
