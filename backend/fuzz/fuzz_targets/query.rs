//! Fuzzes the request target's decoding and routing and both query parses over arbitrary text: each must decide,
//! never panic.
#![no_main]

use store_backend::{query, route};

libfuzzer_sys::fuzz_target!(|data: &[u8]| {
    let text = String::from_utf8_lossy(data);
    let path = query::unquote(&text);
    let _ = route::route(&http::Method::GET, &path);
    let _ = route::route(&http::Method::POST, &path);
    let _ = query::parse_qsl(&text, false, None);
    let _ = query::parse_qsl(&text, true, Some(7));
});
