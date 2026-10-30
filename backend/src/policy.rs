//! The page policy: the content security policy every Store reply carries, computed once from the build.
//!
//! `SvelteKit` hashes each prerendered page's inline scripts into one meta policy of that page (`kit.csp` in hash
//! mode). The Store's `script-src` admits this origin and the union of those hashes, sorted; a page without exactly
//! one meta policy of that exact grammar (a page may name no hash) refuses the whole build, and no build at all
//! admits this origin only.

use std::{
    collections::BTreeSet,
    fs, io,
    path::{Path, PathBuf},
};

use http::HeaderValue;

const META_PREFIX: &str = r#"<meta http-equiv="content-security-policy" content=""#;
const TRUSTED_TYPES: &str = "require-trusted-types-for 'script'; trusted-types svelte-trusted-html";
const BEFORE_SCRIPTS: &str = "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; \
                              form-action 'self'; ";
const AFTER_SCRIPTS: &str = "style-src 'self' 'unsafe-inline'; img-src 'self'; font-src 'self' data:; \
                             connect-src 'self'; frame-src 'none'; worker-src 'self' blob:; manifest-src 'self'; \
                             upgrade-insecure-requests";

/// Why the build admits no page policy; the Store refuses to start.
#[derive(Debug, PartialEq, Eq)]
pub enum PolicyError {
    /// A directory or page of the build could not be read.
    Unreadable(PathBuf),
    /// A page has no meta policy, several, or one outside the build's exact grammar.
    Invalid(PathBuf),
}

/// The page policy of the build at `build`.
///
/// # Errors
///
/// A page could not be read or carries no exact build policy.
///
/// # Panics
///
/// Never: a policy built from this grammar holds only printable ASCII.
pub fn page_policy(build: &Path) -> Result<HeaderValue, PolicyError> {
    let mut sources = BTreeSet::new();
    for page in pages(build)? {
        let document =
            fs::read_to_string(&page).map_err(|_| PolicyError::Unreadable(page.clone()))?;
        sources.extend(page_sources(&document).ok_or(PolicyError::Invalid(page))?);
    }
    let scripts = std::iter::once("'self'")
        .chain(sources.iter().map(String::as_str))
        .collect::<Vec<_>>()
        .join(" ");
    let policy = format!("{BEFORE_SCRIPTS}script-src {scripts}; {TRUSTED_TYPES}; {AFTER_SCRIPTS}");
    Ok(HeaderValue::from_str(&policy).expect("a page policy holds only printable ASCII"))
}

/// Every entry below `build` whose name ends in `.html`, as Python's `rglob("*.html")` lists them: a symbolic link
/// is listed but never descended into.
fn pages(build: &Path) -> Result<Vec<PathBuf>, PolicyError> {
    if fs::symlink_metadata(build).is_err_and(|error| error.kind() == io::ErrorKind::NotFound) {
        return Ok(Vec::new());
    }
    let mut found = Vec::new();
    let mut pending = vec![build.to_path_buf()];
    while let Some(directory) = pending.pop() {
        let unreadable = PolicyError::Unreadable(directory.clone());
        for entry in fs::read_dir(&directory).or(Err(unreadable))? {
            let entry = entry.or(Err(PolicyError::Unreadable(directory.clone())))?;
            let kind = entry
                .file_type()
                .or(Err(PolicyError::Unreadable(entry.path())))?;
            if kind.is_dir() {
                pending.push(entry.path());
            } else if entry.file_name().to_string_lossy().ends_with(".html") {
                found.push(entry.path());
            }
        }
    }
    found.sort();
    Ok(found)
}

/// The hash sources of the one policy the build wrote into a page, which may name none.
#[must_use]
pub fn page_sources(document: &str) -> Option<Vec<String>> {
    let mut policies = document.split(META_PREFIX).skip(1);
    let policy = policies.next()?;
    if policies.next().is_some() {
        return None;
    }
    let (policy, _rest) = policy.split_once('"')?;
    let scripts = policy.strip_suffix(TRUSTED_TYPES)?.strip_suffix("; ")?;
    let mut tokens = scripts.split(' ');
    if tokens.next() != Some("script-src") || tokens.next() != Some("'self'") {
        return None;
    }
    tokens
        .map(|token| sha256_source(token).then(|| token.to_owned()))
        .collect()
}

/// `'sha256-<43 base64 characters>='` exactly.
fn sha256_source(token: &str) -> bool {
    token
        .strip_prefix("'sha256-")
        .and_then(|rest| rest.strip_suffix("='"))
        .is_some_and(|digest| {
            digest.len() == 43
                && digest
                    .bytes()
                    .all(|byte| byte.is_ascii_alphanumeric() || byte == b'+' || byte == b'/')
        })
}

#[cfg(test)]
mod tests;
