//! Fuzzes static path resolution over arbitrary decoded paths against a fixed build: it must answer from inside the
//! build or refuse, never panic.
#![no_main]

use std::{fs, sync::LazyLock};

use store_backend::static_files::Site;

static BUILD: LazyLock<(tempfile::TempDir, Site)> = LazyLock::new(|| {
    let directory = tempfile::tempdir().unwrap();
    let build = directory.path().join("build");
    fs::create_dir_all(build.join("en")).unwrap();
    fs::create_dir_all(build.join("_app/immutable")).unwrap();
    fs::write(build.join("en.html"), "home").unwrap();
    fs::write(build.join("en/404.html"), "missing").unwrap();
    fs::write(build.join("_app/immutable/a.js"), "asset").unwrap();
    fs::write(directory.path().join("secret.txt"), "outside").unwrap();
    let site = Site::new(build);
    (directory, site)
});

libfuzzer_sys::fuzz_target!(|data: &[u8]| {
    let path = String::from_utf8_lossy(data);
    let (_, site) = &*BUILD;
    let reply = site.reply(&path, true);
    assert_ne!(&reply.body[..], b"outside");
});
