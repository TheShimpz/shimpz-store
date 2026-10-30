//! Fuzzes request-id cleaning over arbitrary header bytes: the id is always 1 to 200 token characters.
#![no_main]

use http::{HeaderMap, HeaderValue};

libfuzzer_sys::fuzz_target!(|data: &[u8]| {
    let Ok(value) = HeaderValue::from_bytes(data) else {
        return;
    };
    let mut headers = HeaderMap::new();
    headers.insert("x-request-id", value);
    let id = store_backend::security::request_id(&headers);
    assert!((1..=200).contains(&id.len()));
    assert!(
        id.bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-'))
    );
});
