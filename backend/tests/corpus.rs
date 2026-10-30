//! Replays every case of `tests/corpus/` that reached a new line of the Python Store in the seeded differential, and
//! requires the Rust Store's answer to equal the Python Store's recorded one.

#[path = "support/decide.rs"]
mod decide;

use std::{fs, os::unix::fs::symlink, path::Path};

use strict_json::Value;

fn read(path: &Path) -> Value {
    strict_json::parse(&fs::read(path).unwrap()).unwrap()
}

/// Build the oracle's tree (`[path, contents]` for files, `[path, null, target]` for links) under `work`.
fn build_tree(work: &Path, tree: &Value) {
    let Value::Array(entries) = tree else {
        panic!("a tree is an array");
    };
    for entry in entries {
        let Value::Array(parts) = entry else {
            panic!("a tree entry is an array");
        };
        let (Value::String(relative), contents) = (&parts[0], &parts[1]) else {
            panic!("a tree entry names its path");
        };
        let target = work.join(relative);
        fs::create_dir_all(target.parent().unwrap()).unwrap();
        match (contents, parts.get(2)) {
            (Value::String(contents), _) => fs::write(&target, contents).unwrap(),
            (_, Some(Value::String(link))) => symlink(link, &target).unwrap(),
            other => panic!("a tree entry holds contents or a link: {other:?}"),
        }
    }
}

#[test]
fn the_rust_store_answers_every_corpus_case_as_the_python_store_did() {
    let corpus = Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/corpus");
    let work = tempfile::tempdir().unwrap();
    build_tree(work.path(), &read(&corpus.join("tree.json")));
    let decider = decide::Decider::new(work.path());
    let mut replayed = 0;
    for entry in fs::read_dir(&corpus).unwrap() {
        let path = entry.unwrap().path();
        if path.file_name().unwrap() == "tree.json" {
            continue;
        }
        let Value::Array(cases) = read(&path) else {
            panic!("a corpus file is an array");
        };
        for recorded in &cases {
            let (Some(case), Some(Value::String(python))) =
                (recorded.get("case"), recorded.get("python"))
            else {
                panic!("a corpus entry holds its case and the Python answer");
            };
            assert_eq!(
                &decider.decide(case),
                python,
                "{}: {case:?}",
                path.display()
            );
            replayed += 1;
        }
    }
    assert!(replayed > 500, "{replayed} corpus cases");
}
