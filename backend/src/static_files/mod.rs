//! The prerendered build: a request path resolves to one regular file inside the build, symbolic links resolved,
//! served whole with its closed media type and integer validators; a page miss answers the localized not-found
//! page for an HTML navigation and plain `not found` otherwise.

pub mod headers;

use std::{
    fs::{self, File},
    io::Read,
    os::unix::fs::MetadataExt,
    path::{Path, PathBuf},
};

use http::{HeaderName, HeaderValue, StatusCode, header};

use crate::response::Reply;

/// The cache policy of every page and mutable file: revalidate before each use.
pub const HTML_CACHE: &str = "public, no-cache, max-age=0, must-revalidate, no-transform";
/// The cache policy of content-addressed build assets and verified icons.
pub const IMMUTABLE_CACHE: &str = "public, max-age=31536000, immutable";
/// Where the site root sends every visitor.
pub const ROOT_LOCATION: &str = "/en";

/// The prerendered build a Store serves.
#[derive(Clone, Debug)]
pub struct Site {
    build: PathBuf,
}

impl Site {
    /// The build at `build`.
    #[must_use]
    pub fn new(build: PathBuf) -> Self {
        Self { build }
    }

    /// The reply to `GET /{path}`, for an HTML navigation or not.
    #[must_use]
    pub fn reply(&self, path: &str, navigation: bool) -> Reply {
        let root = fs::canonicalize(&self.build).ok();
        let hit = root.as_deref().and_then(|root| resolve(root, path));
        if let (Some(root), Some(hit)) = (root.as_deref(), hit.as_deref()) {
            if !not_found_document(root, hit) {
                return file(hit, StatusCode::OK, cache_control(path, hit));
            }
            if navigation {
                return file(hit, StatusCode::NOT_FOUND, HTML_CACHE);
            }
        }
        if let (true, Some(root)) = (navigation, root.as_deref())
            && let Some(document) = localized_not_found(root, path)
        {
            return file(&document, StatusCode::NOT_FOUND, HTML_CACHE);
        }
        Reply::new(
            StatusCode::NOT_FOUND,
            vec![(header::CACHE_CONTROL, HeaderValue::from_static(HTML_CACHE))],
            Some("text/plain; charset=utf-8"),
            &b"not found"[..],
        )
    }
}

/// The `308` the site root answers.
#[must_use]
pub fn root_redirect() -> Reply {
    Reply::redirect(
        StatusCode::PERMANENT_REDIRECT,
        HeaderValue::from_static(ROOT_LOCATION),
        vec![(header::CACHE_CONTROL, HeaderValue::from_static(HTML_CACHE))],
    )
}

/// The one regular file inside `root` a request path names: the path itself, with `.html`, or its `index.html`.
///
/// A path with a C0 control character or a `..` segment names none.
fn resolve(root: &Path, path: &str) -> Option<PathBuf> {
    if path.chars().any(|character| character < ' ') {
        return None;
    }
    let relative = path.trim_matches('/');
    if relative.split('/').any(|segment| segment == "..") {
        return None;
    }
    let index = if relative.is_empty() {
        String::from("index.html")
    } else {
        format!("{relative}/index.html")
    };
    [relative.to_owned(), format!("{relative}.html"), index]
        .iter()
        .find_map(|candidate| inside(root, candidate))
}

/// `root/candidate`, symbolic links resolved, when it is a regular file strictly inside `root`.
fn inside(root: &Path, candidate: &str) -> Option<PathBuf> {
    let resolved = fs::canonicalize(root.join(candidate)).ok()?;
    let within = resolved.starts_with(root) && resolved != root;
    (within && resolved.is_file()).then_some(resolved)
}

/// Whether a resolved file is a locale's not-found page, `<locale>/404.html`, which is never a successful page.
fn not_found_document(root: &Path, hit: &Path) -> bool {
    hit.strip_prefix(root)
        .is_ok_and(|relative| relative.components().count() == 2 && relative.ends_with("404.html"))
}

/// The not-found page of the path's first segment, else English's.
fn localized_not_found(root: &Path, path: &str) -> Option<PathBuf> {
    let first = path.trim_matches('/').split('/').next().unwrap_or_default();
    [format!("{first}/404"), String::from("en/404")]
        .iter()
        .filter_map(|candidate| resolve(root, candidate))
        .find(|document| not_found_document(root, document))
}

/// Revalidate pages and mutable files; keep `SvelteKit`'s content-addressed assets for a year.
fn cache_control(path: &str, hit: &Path) -> &'static str {
    let name = hit.file_name().unwrap_or_default().to_string_lossy();
    let page = matches!(headers::suffix(&name).as_str(), ".html" | ".htm");
    if !page && path.trim_matches('/').starts_with("_app/immutable/") {
        IMMUTABLE_CACHE
    } else {
        HTML_CACHE
    }
}

/// One whole build file, read now, with its cache policy, media type, length, Last-Modified, and entity tag.
///
/// # Panics
///
/// When the file vanished or became unreadable after it resolved: the request then answers the closed 500.
fn file(path: &Path, status: StatusCode, cache: &'static str) -> Reply {
    let mut opened = File::open(path).expect("a resolved build file opens");
    let metadata = opened.metadata().expect("an open build file has metadata");
    let mut body = Vec::new();
    opened
        .read_to_end(&mut body)
        .expect("an open build file reads");
    let name = path.file_name().unwrap_or_default().to_string_lossy();
    let mtime_ns = i128::from(metadata.mtime()) * 1_000_000_000 + i128::from(metadata.mtime_nsec());
    let mut headers: Vec<(HeaderName, HeaderValue)> = vec![
        (header::CACHE_CONTROL, HeaderValue::from_static(cache)),
        (
            header::CONTENT_TYPE,
            HeaderValue::from_static(headers::media_type(&name)),
        ),
        (header::CONTENT_LENGTH, HeaderValue::from(body.len())),
    ];
    if let Some(modified) = headers::last_modified(mtime_ns) {
        headers.push((header::LAST_MODIFIED, value(&modified)));
    }
    headers.push((
        header::ETAG,
        value(&headers::entity_tag(mtime_ns, metadata.len())),
    ));
    Reply {
        status,
        headers,
        body: body.into(),
    }
}

fn value(text: &str) -> HeaderValue {
    HeaderValue::from_str(text).expect("a validator holds only printable ASCII")
}

#[cfg(test)]
mod tests;
