//! Routing on the percent-decoded path, exactly as the Python Store's Starlette routes matched it.
//!
//! Routes are tried in order: the OAuth broker, the public API, then the site. The first route whose path and
//! method both match answers; otherwise the first whose path matches answers 405 with its methods in `Allow`;
//! otherwise 404. Every route pattern was a Python regular expression anchored with `^…$`, and Python's `$` also
//! matches before one final newline: `/api/health\n` is the health route, and the site route's path parameter is
//! everything after the first `/` except one final newline, with no other newline in it.

use http::Method;

/// The OAuth start route, which the documentation names as the Store's consent entrance.
pub const OAUTH_START_PATH: &str = "/api/oauth/cloudflare/start";
/// The OAuth callback route, whose response may set its own content security policy.
pub const OAUTH_CALLBACK_PATH: &str = "/api/oauth/cloudflare/callback";
const ICON_PREFIX: &str = "/api/assistant-icons/";

/// One route a request selected, with the path parameters it carries.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Route<'a> {
    /// `GET /api/oauth/cloudflare/start`.
    Start,
    /// `GET /api/oauth/cloudflare/callback`.
    Callback,
    /// `POST /api/oauth/cloudflare/claim`.
    Claim,
    /// `POST /api/oauth/cloudflare/refresh`.
    Refresh,
    /// `POST /api/oauth/cloudflare/revoke`.
    Revoke,
    /// `GET /api/health`.
    Health,
    /// `GET /api/assistants`.
    Catalog,
    /// `GET /api/assistant-icons/{source}/{icon}.png`.
    Icon {
        /// The publication's source digest as the path names it.
        source: &'a str,
        /// The icon's digest as the path names it.
        icon: &'a str,
    },
    /// `GET` or `HEAD /`.
    Root,
    /// `GET /{path}`: a file of the prerendered build.
    Site {
        /// Everything after the first `/`, without one final newline.
        path: &'a str,
    },
}

/// What routing decided for one request.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Outcome<'a> {
    /// A route whose path and method match.
    Matched(Route<'a>),
    /// A route matched the path but not the method; its methods.
    NotAllowed(&'static str),
    /// No route matched the path.
    NotFound,
}

type Matcher = for<'a> fn(&'a str) -> Option<Route<'a>>;

const ROUTES: [(Matcher, Method, &str); 11] = [
    (
        |path| literal(path, OAUTH_START_PATH).then_some(Route::Start),
        Method::GET,
        "GET",
    ),
    (
        |path| literal(path, OAUTH_CALLBACK_PATH).then_some(Route::Callback),
        Method::GET,
        "GET",
    ),
    (
        |path| literal(path, "/api/oauth/cloudflare/claim").then_some(Route::Claim),
        Method::POST,
        "POST",
    ),
    (
        |path| literal(path, "/api/oauth/cloudflare/refresh").then_some(Route::Refresh),
        Method::POST,
        "POST",
    ),
    (
        |path| literal(path, "/api/oauth/cloudflare/revoke").then_some(Route::Revoke),
        Method::POST,
        "POST",
    ),
    (
        |path| literal(path, "/api/health").then_some(Route::Health),
        Method::GET,
        "GET",
    ),
    (
        |path| literal(path, "/api/assistants").then_some(Route::Catalog),
        Method::GET,
        "GET",
    ),
    (icon, Method::GET, "GET"),
    (
        |path| literal(path, "/").then_some(Route::Root),
        Method::GET,
        "GET",
    ),
    (
        |path| literal(path, "/").then_some(Route::Root),
        Method::HEAD,
        "HEAD",
    ),
    (site, Method::GET, "GET"),
];

/// Route one request by its method and percent-decoded path.
#[must_use]
pub fn route<'a>(method: &Method, path: &'a str) -> Outcome<'a> {
    let mut partial = None;
    for (matcher, allowed, allow) in &ROUTES {
        if let Some(selected) = matcher(path) {
            if method == allowed {
                return Outcome::Matched(selected);
            }
            partial = partial.or(Some(*allow));
        }
    }
    partial.map_or(Outcome::NotFound, Outcome::NotAllowed)
}

/// Python's `$`: the end of the text, or the position before one final newline.
fn at_end(rest: &str) -> bool {
    rest.is_empty() || rest == "\n"
}

fn literal(path: &str, literal: &str) -> bool {
    path.strip_prefix(literal).is_some_and(at_end)
}

/// `^/(?P<path>.*)$`, where `.` is any character but a newline.
fn site(path: &str) -> Option<Route<'_>> {
    let rest = path.strip_prefix('/')?;
    let body = rest.strip_suffix('\n').unwrap_or(rest);
    (!body.contains('\n')).then_some(Route::Site { path: body })
}

/// `^/api/assistant-icons/(?P<source>[^/]+)/(?P<icon>[^/]+)\.png$`, the icon group as long as it can be.
fn icon(path: &str) -> Option<Route<'_>> {
    let (source, rest) = path.strip_prefix(ICON_PREFIX)?.split_once('/')?;
    if source.is_empty() || rest.contains('/') {
        return None;
    }
    let icon = rest
        .strip_suffix(".png")
        .or_else(|| rest.strip_suffix(".png\n"))?;
    (!icon.is_empty()).then_some(Route::Icon { source, icon })
}

#[cfg(test)]
mod tests;
