use std::{
    fs::{self, File},
    path::Path,
    time::{Duration, UNIX_EPOCH},
};

use http::{HeaderValue, StatusCode, header};

use super::{HTML_CACHE, IMMUTABLE_CACHE, Site, root_redirect};
use crate::response::Reply;

fn write(root: &Path, relative: &str, content: &str) {
    let target = root.join(relative);
    fs::create_dir_all(target.parent().unwrap()).unwrap();
    fs::write(target, content).unwrap();
}

fn build() -> tempfile::TempDir {
    let build = tempfile::tempdir().unwrap();
    for (relative, content) in [
        ("en.html", "english-home"),
        ("en/about.html", "about"),
        ("en/404.html", "english-not-found"),
        ("pt/404.html", "portuguese-not-found"),
        ("pt/guide/index.html", "guide"),
        (".html", "dot-page"),
        ("_app/immutable/chunk.js", "export default true"),
        ("_app/immutable/never-cache.html", "html"),
        ("_app/immutable-lookalike/chunk.js", "mutable"),
        ("brand/mark.svg", "<svg></svg>"),
    ] {
        write(build.path(), relative, content);
    }
    build
}

fn header<'a>(reply: &'a Reply, name: &header::HeaderName) -> &'a str {
    reply.header(name).unwrap().to_str().unwrap()
}

fn body(reply: &Reply) -> &str {
    std::str::from_utf8(&reply.body).unwrap()
}

#[test]
fn pages_and_files_resolve_with_their_html_and_index_forms() {
    let build = build();
    let site = Site::new(build.path().to_path_buf());
    for (path, expected) in [
        ("en", "english-home"),
        ("en.html", "english-home"),
        ("en/", "english-home"),
        ("en//about", "about"),
        ("pt/guide", "guide"),
        ("", "dot-page"),
        ("./en", "english-home"),
    ] {
        let reply = site.reply(path, false);
        assert_eq!(
            (reply.status, body(&reply)),
            (StatusCode::OK, expected),
            "{path}"
        );
    }
}

#[test]
fn html_navigation_always_revalidates() {
    let build = build();
    let site = Site::new(build.path().to_path_buf());
    let page = site.reply("en", true);
    assert_eq!(
        header(&page, &header::CONTENT_TYPE),
        "text/html; charset=utf-8"
    );
    assert_eq!(header(&page, &header::CONTENT_LENGTH), "12");
    assert_eq!(header(&page, &header::CACHE_CONTROL), HTML_CACHE);
    let never = site.reply("_app/immutable/never-cache.html", true);
    assert_eq!(header(&never, &header::CACHE_CONTROL), HTML_CACHE);
}

#[test]
fn sveltekit_immutable_assets_keep_long_content_addressed_cache() {
    let build = build();
    let site = Site::new(build.path().to_path_buf());
    let asset = site.reply("/_app/immutable/chunk.js", false);
    assert_eq!(header(&asset, &header::CACHE_CONTROL), IMMUTABLE_CACHE);
    assert_eq!(
        header(&asset, &header::CONTENT_TYPE),
        "text/javascript; charset=utf-8"
    );
}

#[test]
fn mutable_assets_and_missing_navigation_do_not_heuristically_cache() {
    let build = build();
    let site = Site::new(build.path().to_path_buf());
    for path in ["_app/immutable-lookalike/chunk.js", "brand/mark.svg"] {
        assert_eq!(
            header(&site.reply(path, false), &header::CACHE_CONTROL),
            HTML_CACHE,
            "{path}"
        );
    }
    for navigation in [true, false] {
        let missing = site.reply("missing", navigation);
        assert_eq!(header(&missing, &header::CACHE_CONTROL), HTML_CACHE);
    }
}

#[test]
fn a_served_file_carries_its_integer_validators() {
    let build = build();
    let page = build.path().join("en.html");
    File::options()
        .write(true)
        .open(&page)
        .unwrap()
        .set_modified(UNIX_EPOCH + Duration::new(1_700_000_000, 999_999_999))
        .unwrap();
    let old = build.path().join("brand/mark.svg");
    File::options()
        .write(true)
        .open(&old)
        .unwrap()
        .set_modified(UNIX_EPOCH - Duration::from_nanos(1))
        .unwrap();
    let site = Site::new(build.path().to_path_buf());
    let reply = site.reply("en", false);
    assert_eq!(header(&reply, &header::ETAG), "\"17979cfe71c4c9ff-c\"");
    assert_eq!(
        header(&reply, &header::LAST_MODIFIED),
        "Tue, 14 Nov 2023 22:13:20 GMT"
    );
    let before = site.reply("brand/mark.svg", false);
    assert_eq!(header(&before, &header::ETAG), "\"-1-b\"");
    assert_eq!(before.header(&header::LAST_MODIFIED), None);
}

#[test]
fn html_misses_serve_localized_not_found_document() {
    let build = build();
    let site = Site::new(build.path().to_path_buf());
    for (path, expected) in [
        ("pt/missing", "portuguese-not-found"),
        ("xx/missing", "english-not-found"),
        ("missing", "english-not-found"),
        ("pt/404", "portuguese-not-found"),
        ("pt/404.html", "portuguese-not-found"),
        ("\0/x", "english-not-found"),
    ] {
        let reply = site.reply(path, true);
        assert_eq!(
            (reply.status, body(&reply)),
            (StatusCode::NOT_FOUND, expected),
            "{path}"
        );
        assert_eq!(header(&reply, &header::CACHE_CONTROL), HTML_CACHE);
    }
}

fn plain_not_found(site: &Site, path: &str) {
    let reply = site.reply(path, false);
    assert_eq!(
        (reply.status, body(&reply)),
        (StatusCode::NOT_FOUND, "not found"),
        "{path}"
    );
    assert_eq!(
        header(&reply, &header::CONTENT_TYPE),
        "text/plain; charset=utf-8"
    );
}

#[test]
fn not_found_document_is_never_exposed_as_a_successful_page() {
    let build = build();
    let site = Site::new(build.path().to_path_buf());
    plain_not_found(&site, "en/404");
    let navigation = site.reply("en/404.html", true);
    assert_eq!(
        (navigation.status, body(&navigation)),
        (StatusCode::NOT_FOUND, "english-not-found")
    );
}

#[test]
fn non_html_miss_keeps_plain_text_response() {
    let build = build();
    let site = Site::new(build.path().to_path_buf());
    for path in [
        "missing.js",
        "en%",
        "../en",
        "en/../en",
        "_app",
        &"x".repeat(5000),
    ] {
        plain_not_found(&site, path);
    }
}

#[test]
fn missing_not_found_document_and_foreign_path_fail_closed() {
    let build = build();
    let absent = Site::new(build.path().join("absent"));
    assert_eq!(body(&absent.reply("en", true)), "not found");
    let bare = tempfile::tempdir().unwrap();
    write(bare.path(), "pt/page.html", "page");
    assert_eq!(
        body(&Site::new(bare.path().to_path_buf()).reply("pt/missing", true)),
        "not found"
    );
}

#[test]
fn a_path_holding_a_control_byte_names_no_file() {
    let build = build();
    let site = Site::new(build.path().to_path_buf());
    for path in ["en\0", "en\n", "\u{1f}en"] {
        plain_not_found(&site, path);
    }
    let navigation = site.reply("\0/x", true);
    assert_eq!(body(&navigation), "english-not-found");
}

#[test]
fn a_range_request_receives_the_whole_file_without_advertising_ranges() {
    let build = build();
    let site = Site::new(build.path().to_path_buf());
    let page = site.reply("en", false);
    assert_eq!(body(&page), "english-home");
    assert_eq!(page.header(&header::ACCEPT_RANGES), None);
    assert_eq!(page.header(&header::CONTENT_RANGE), None);
}

#[test]
fn files_resolving_outside_the_build_are_refused_while_a_linked_build_serves() {
    let parent = tempfile::tempdir().unwrap();
    let build = parent.path().join("build");
    write(&build, "en.html", "home");
    write(parent.path(), "secret.txt", "secret sentinel");
    std::os::unix::fs::symlink(parent.path().join("secret.txt"), build.join("leak.txt")).unwrap();
    std::os::unix::fs::symlink(&build, parent.path().join("linked-build")).unwrap();
    let site = Site::new(parent.path().join("linked-build"));
    assert_eq!(body(&site.reply("leak.txt", true)), "not found");
    assert_eq!(body(&site.reply("en", false)), "home");
}

#[test]
fn the_site_root_sends_every_visitor_to_the_english_home() {
    let reply = root_redirect();
    assert_eq!(reply.status, StatusCode::PERMANENT_REDIRECT);
    assert_eq!(
        reply.header(&header::LOCATION),
        Some(&HeaderValue::from_static("/en"))
    );
    assert_eq!(header(&reply, &header::CACHE_CONTROL), HTML_CACHE);
}
