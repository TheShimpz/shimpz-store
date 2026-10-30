use std::{fs, os::unix::fs::symlink, path::Path};

use super::realpath;

fn resolved(path: &Path) -> String {
    realpath(path.as_os_str()).to_string_lossy().into_owned()
}

#[test]
fn components_resolve_lexically_and_links_in_place() {
    let directory = tempfile::tempdir().unwrap();
    let root = fs::canonicalize(directory.path()).unwrap();
    fs::create_dir(root.join("build")).unwrap();
    fs::write(root.join("build/page.html"), "page").unwrap();
    fs::write(root.join("secret.txt"), "secret").unwrap();
    symlink("page.html", root.join("build/relative")).unwrap();
    symlink(root.join("secret.txt"), root.join("build/absolute")).unwrap();
    symlink("../secret.txt", root.join("build/up")).unwrap();
    let base = root.display().to_string();
    let cases = [
        ("build/page.html/.", "build/page.html"),
        ("build//./page.html", "build/page.html"),
        ("build/page.html/missing", "build/page.html/missing"),
        ("build/relative", "build/page.html"),
        ("build/relative/.", "build/page.html"),
        ("build/up", "secret.txt"),
        ("build/missing/../page.html", "build/page.html"),
        ("build/relative/../relative", "build/page.html"),
    ];
    for (path, expected) in cases {
        assert_eq!(
            resolved(&root.join(path)),
            format!("{base}/{expected}"),
            "{path}"
        );
    }
    assert_eq!(
        resolved(&root.join("build/absolute")),
        format!("{base}/secret.txt")
    );
}

#[test]
fn the_root_has_no_parent_and_a_link_loop_stays_unresolved() {
    assert_eq!(resolved(Path::new("/..")), "/");
    assert_eq!(resolved(Path::new("/../tmp/..")), "/");
    let directory = tempfile::tempdir().unwrap();
    let root = fs::canonicalize(directory.path()).unwrap();
    symlink("b", root.join("a")).unwrap();
    symlink("a", root.join("b")).unwrap();
    assert_eq!(resolved(&root.join("a")), format!("{}/a", root.display()));
}
