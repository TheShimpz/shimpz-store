//! Fuzzes reading the egress's CONNECT reply head over arbitrary bytes: it must end, never panic or grow unbounded.
#![no_main]

libfuzzer_sys::fuzz_target!(|data: &[u8]| {
    let runtime = tokio::runtime::Builder::new_current_thread()
        .build()
        .unwrap();
    let mut reader: &[u8] = data;
    let _ = runtime.block_on(store_backend::oauth::tunnel::proxy_response(&mut reader));
});
