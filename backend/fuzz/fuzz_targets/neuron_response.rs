//! Fuzzes the Neuron reply checks (T11 consent URL, token shapes, T15 acknowledgement) over arbitrary JSON bytes.
#![no_main]

use store_backend::oauth::{neuron, shape::Scopes};

libfuzzer_sys::fuzz_target!(|data: &[u8]| {
    let Ok(reply) = strict_json::parse(data) else {
        return;
    };
    let scopes = Scopes::sorted(&["dns.read", "zone.read"]).unwrap();
    let binding = "S".repeat(43);
    let _ = neuron::consent(&reply, &binding, &binding, &scopes);
    let _ = neuron::tokens(&reply, &scopes);
    let _ = neuron::acknowledged(&reply);
});
