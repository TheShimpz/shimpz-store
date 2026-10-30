//! Python's non-strict `os.path.realpath` for absolute paths, which the Python Store resolved build files with.
//!
//! Components are taken in order: empty and `.` components are skipped, `..` drops the last resolved component
//! lexically, and every other component is appended; when `lstat` shows the result is a symbolic link, its target's
//! components are resolved in its place (an absolute target restarts from `/`), each link once, a link met again
//! while it is still being resolved staying unresolved. A component `lstat` cannot read is appended as it is, so a
//! regular file followed by `.` is the file itself.

use std::{
    collections::HashMap,
    ffi::{OsStr, OsString},
    fs,
    os::unix::ffi::{OsStrExt, OsStringExt},
    path::PathBuf,
};

/// One unprocessed part of the path: a component, or the marker that a link's target is fully resolved.
enum Part {
    Component(Vec<u8>),
    Resolved(Vec<u8>),
}

/// The canonical form of the absolute path `filename`, as Python's `os.path.realpath(filename)` computes it.
#[must_use]
pub fn realpath(filename: &OsStr) -> PathBuf {
    let mut rest: Vec<Part> = components(filename.as_bytes());
    let mut path = b"/".to_vec();
    let mut seen: HashMap<Vec<u8>, Option<Vec<u8>>> = HashMap::new();
    while let Some(part) = rest.pop() {
        let name = match part {
            Part::Resolved(link) => {
                seen.insert(link, Some(path.clone()));
                continue;
            }
            Part::Component(name) => name,
        };
        if name.is_empty() || name == b"." {
            continue;
        }
        if name == b".." {
            let parent = path
                .iter()
                .rposition(|byte| *byte == b'/')
                .unwrap_or_default();
            path.truncate(parent.max(1));
            continue;
        }
        path = step(path, &name, &mut rest, &mut seen);
    }
    PathBuf::from(OsString::from_vec(path))
}

/// The path after appending `name` to `path`: the joined path, a link's cached resolution, or, for a link to
/// resolve, `path` itself (`/` for an absolute target) with the target's components pushed.
fn step(
    path: Vec<u8>,
    name: &[u8],
    rest: &mut Vec<Part>,
    seen: &mut HashMap<Vec<u8>, Option<Vec<u8>>>,
) -> Vec<u8> {
    let newpath = joined(&path, name);
    // Only a symbolic link has a target: anything else, or a path that cannot be read, is appended as it is.
    let Ok(target) = fs::read_link(OsStr::from_bytes(&newpath)) else {
        return newpath;
    };
    if let Some(known) = seen.get(&newpath) {
        return known.clone().unwrap_or(newpath);
    }
    let target = target.into_os_string().into_vec();
    seen.insert(newpath.clone(), None);
    rest.push(Part::Resolved(newpath.clone()));
    rest.extend(components(&target));
    if target.starts_with(b"/") {
        b"/".to_vec()
    } else {
        path
    }
}

/// `path` with `name` appended after one separator.
fn joined(path: &[u8], name: &[u8]) -> Vec<u8> {
    let mut joined = path.to_vec();
    if path != b"/" {
        joined.push(b'/');
    }
    joined.extend_from_slice(name);
    joined
}

/// The components of `text` as a stack: the first component on top.
fn components(text: &[u8]) -> Vec<Part> {
    text.split(|byte| *byte == b'/')
        .rev()
        .map(|component| Part::Component(component.to_vec()))
        .collect()
}

#[cfg(test)]
mod tests;
