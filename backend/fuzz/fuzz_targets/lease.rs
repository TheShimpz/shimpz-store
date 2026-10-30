//! Fuzzes lease verification over arbitrary text under a fixed two-key ring: it must verify or refuse.
#![no_main]

use std::{
    fs,
    os::unix::fs::PermissionsExt,
    path::PathBuf,
    sync::{Arc, LazyLock},
};

use store_backend::{clock::ManualClock, oauth::lease::LeaseSigner};

static RING: LazyLock<(tempfile::TempDir, LeaseSigner)> = LazyLock::new(|| {
    let directory = tempfile::tempdir().unwrap();
    let install = |name: &str, key: &[u8]| -> PathBuf {
        let path = directory.path().join(name);
        fs::write(&path, key).unwrap();
        fs::set_permissions(&path, fs::Permissions::from_mode(0o400)).unwrap();
        path
    };
    let paths = [
        install("lease-key", &[b'n'; 32]),
        install("lease-key-previous", &[b'q'; 32]),
    ];
    let signer = LeaseSigner::new(paths, Arc::new(ManualClock::at(1_800_000_000)));
    (directory, signer)
});

libfuzzer_sys::fuzz_target!(|data: &[u8]| {
    let text = String::from_utf8_lossy(data);
    let (_, signer) = &*RING;
    let _ = signer.verify(&text, "access-token-0001", None);
    let _ = signer.verify(&text, "refresh-token-001", Some("dns.read zone.read"));
});
