use std::{fs, os::unix::fs::PermissionsExt};

use super::{PolicyError, page_policy};

const FIRST: &str = "'sha256-E2N7hQ3NwGfqO4gTMTO7EKdeuUdNjqWRsO93pk0dKzQ='";
const SECOND: &str = "'sha256-JY9Zlt5CTKKcht1Ime1WdiZbsBz8Z7rPGggLHARyZHw='";
/// A digest whose base64 needs `+` and `/`.
const THIRD: &str = "'sha256-+/9Zlt5CTKKcht1Ime1WdiZbsBz8Z7rPGggLHARyZHw='";
const TRUSTED: &str = "require-trusted-types-for 'script'; trusted-types svelte-trusted-html";

fn page(scripts: &str) -> String {
    exact(&format!("{scripts}; {TRUSTED}"))
}

fn exact(policy: &str) -> String {
    format!(
        "<!doctype html><head><meta charset=\"utf-8\" />\n<meta http-equiv=\"content-security-policy\" \
         content=\"{policy}\">\n</head><body><script>start()</script></body>"
    )
}

fn header(scripts: &str) -> String {
    format!(
        "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; \
         script-src {scripts}; {TRUSTED}; style-src 'self' 'unsafe-inline'; img-src 'self'; font-src 'self' data:; \
         connect-src 'self'; frame-src 'none'; worker-src 'self' blob:; manifest-src 'self'; upgrade-insecure-requests"
    )
}

#[test]
fn the_build_inline_scripts_are_admitted_by_their_exact_hashes() {
    let build = tempfile::tempdir().unwrap();
    fs::create_dir_all(build.path().join("en")).unwrap();
    fs::write(
        build.path().join("en.html"),
        page(&format!("script-src 'self' {SECOND}")),
    )
    .unwrap();
    fs::write(
        build.path().join("en/about.html"),
        page(&format!("script-src 'self' {SECOND} {FIRST}")),
    )
    .unwrap();
    fs::write(build.path().join("en/404.html"), page("script-src 'self'")).unwrap();
    fs::write(
        build.path().join("pt.html"),
        page(&format!("script-src 'self' {THIRD}")),
    )
    .unwrap();
    fs::write(build.path().join("robots.txt"), "not a page").unwrap();
    std::os::unix::fs::symlink(build.path().join("en"), build.path().join("linked")).unwrap();
    let policy = page_policy(build.path()).unwrap();
    assert_eq!(
        policy.to_str().unwrap(),
        header(&format!("'self' {THIRD} {FIRST} {SECOND}"))
    );
}

#[test]
fn without_a_build_only_this_origin_may_run_scripts() {
    let build = tempfile::tempdir().unwrap();
    assert_eq!(
        page_policy(&build.path().join("absent"))
            .unwrap()
            .to_str()
            .unwrap(),
        header("'self'")
    );
    assert_eq!(
        page_policy(build.path()).unwrap().to_str().unwrap(),
        header("'self'")
    );
}

#[test]
fn a_page_without_one_exact_build_policy_refuses_the_whole_build() {
    let documents = [
        "<!doctype html><script>start()</script>".to_owned(),
        page(&format!("script-src 'self' 'unsafe-inline' {FIRST}")),
        page(&format!("script-src 'self' {FIRST} https://cdn.example")),
        page(&format!("default-src 'self' {FIRST}")),
        page(&format!("script-src {FIRST}")),
        page("script-src 'self' 'sha256-short='"),
        page(&format!("script-src 'self' 'sha256-{}='", "!".repeat(43))),
        page(&format!("script-src  'self' {FIRST}")),
        exact(&format!("script-src 'self' {FIRST}")),
        exact(&format!("script-src 'self' {FIRST}{TRUSTED}")),
        exact(&format!("script-src 'self' {FIRST}; {TRUSTED} default")),
        page(&format!("script-src 'self' {FIRST}")).repeat(2),
        "<meta http-equiv=\"content-security-policy\" content=\"script-src".to_owned(),
        page(&format!("script-src 'self' {FIRST}")).replace("'self'", "'none'"),
    ];
    for document in documents {
        let build = tempfile::tempdir().unwrap();
        let path = build.path().join(".html");
        fs::write(&path, &document).unwrap();
        assert_eq!(
            page_policy(build.path()),
            Err(PolicyError::Invalid(path)),
            "{document}"
        );
    }
}

#[test]
fn an_unreadable_build_refuses_to_start() {
    let build = tempfile::tempdir().unwrap();
    let page = build.path().join("en.html");
    fs::write(&page, [0xff, 0xfe]).unwrap();
    assert_eq!(
        page_policy(build.path()),
        Err(PolicyError::Unreadable(page))
    );
    let locked = tempfile::tempdir().unwrap();
    let directory = locked.path().join("private");
    fs::create_dir(&directory).unwrap();
    fs::set_permissions(&directory, fs::Permissions::from_mode(0o000)).unwrap();
    let refused = page_policy(locked.path());
    fs::set_permissions(&directory, fs::Permissions::from_mode(0o700)).unwrap();
    assert_eq!(refused, Err(PolicyError::Unreadable(directory)));
    let file = tempfile::NamedTempFile::new().unwrap();
    assert_eq!(
        page_policy(file.path()),
        Err(PolicyError::Unreadable(file.path().to_path_buf()))
    );
    let hidden = tempfile::tempdir().unwrap();
    let parent = hidden.path().join("locked");
    fs::create_dir(&parent).unwrap();
    fs::set_permissions(&parent, fs::Permissions::from_mode(0o000)).unwrap();
    let refused = page_policy(&parent.join("build"));
    fs::set_permissions(&parent, fs::Permissions::from_mode(0o700)).unwrap();
    assert_eq!(refused, Err(PolicyError::Unreadable(parent.join("build"))));
}

fn directives(policy: &str) -> Vec<String> {
    policy.split("; ").map(str::to_owned).collect()
}

#[test]
fn no_response_admits_unsafe_inline_scripts() {
    let build = tempfile::tempdir().unwrap();
    fs::write(
        build.path().join("en.html"),
        page(&format!("script-src 'self' {FIRST} {SECOND}")),
    )
    .unwrap();
    let policy = page_policy(build.path()).unwrap();
    let scripts = directives(policy.to_str().unwrap())
        .into_iter()
        .find(|directive| directive.starts_with("script-src "))
        .unwrap();
    assert_eq!(scripts, format!("script-src 'self' {FIRST} {SECOND}"));
    assert!(!scripts.contains("'unsafe-inline'"));
}

#[test]
fn every_response_refuses_plain_strings_at_dom_injection_sinks() {
    let build = tempfile::tempdir().unwrap();
    let policy = directives(page_policy(build.path()).unwrap().to_str().unwrap());
    assert!(policy.contains(&"require-trusted-types-for 'script'".to_owned()));
    assert!(policy.contains(&"trusted-types svelte-trusted-html".to_owned()));
}

#[test]
fn pages_load_images_and_open_connections_only_from_this_origin() {
    let build = tempfile::tempdir().unwrap();
    let policy = directives(
        page_policy(&build.path().join("absent"))
            .unwrap()
            .to_str()
            .unwrap(),
    );
    assert!(policy.contains(&"img-src 'self'".to_owned()));
    assert!(policy.contains(&"connect-src 'self'".to_owned()));
}
