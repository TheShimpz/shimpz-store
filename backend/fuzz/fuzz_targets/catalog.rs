//! Fuzzes the catalog projection over arbitrary Developers bytes: strict JSON, then the closed projection.
#![no_main]

libfuzzer_sys::fuzz_target!(|data: &[u8]| {
    if let Ok(value) = strict_json::parse(data) {
        let _ = store_backend::catalog::project::project(&value, "en");
    }
});
