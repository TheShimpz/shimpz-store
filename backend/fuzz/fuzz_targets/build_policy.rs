//! Fuzzes the build pages' meta policy parser over arbitrary documents: it must read one policy or refuse.
#![no_main]

libfuzzer_sys::fuzz_target!(|data: &[u8]| {
    let _ = store_backend::policy::page_sources(&String::from_utf8_lossy(data));
});
