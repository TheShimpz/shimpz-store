//! Fuzzes the start limit's client key over arbitrary `CF-Connecting-IP` bytes from a trusted proxy.
#![no_main]

use std::{ffi::OsStr, net::IpAddr};

use http::{HeaderMap, HeaderValue};
use store_backend::ratelimit::{client_key, trusted_proxies};

libfuzzer_sys::fuzz_target!(|data: &[u8]| {
    let Ok(value) = HeaderValue::from_bytes(data) else {
        return;
    };
    let mut headers = HeaderMap::new();
    headers.insert("cf-connecting-ip", value);
    let proxies = trusted_proxies(Some(OsStr::new("10.0.0.0/24"))).unwrap();
    let _ = client_key(IpAddr::from([10, 0, 0, 2]), &headers, &proxies);
});
