use http::Method;

use super::{Outcome, Route, route};

#[test]
fn every_route_answers_only_its_method() {
    let cases = [
        ("/api/oauth/cloudflare/start", Method::GET, Route::Start),
        (
            "/api/oauth/cloudflare/callback",
            Method::GET,
            Route::Callback,
        ),
        ("/api/oauth/cloudflare/claim", Method::POST, Route::Claim),
        (
            "/api/oauth/cloudflare/refresh",
            Method::POST,
            Route::Refresh,
        ),
        ("/api/oauth/cloudflare/revoke", Method::POST, Route::Revoke),
        ("/api/health", Method::GET, Route::Health),
        ("/api/assistants", Method::GET, Route::Catalog),
        ("/", Method::GET, Route::Root),
        ("/", Method::HEAD, Route::Root),
        ("/en", Method::GET, Route::Site { path: "en" }),
    ];
    for (path, method, expected) in cases {
        assert_eq!(
            route(&method, path),
            Outcome::Matched(expected),
            "{method} {path}"
        );
    }
}

#[test]
fn another_method_answers_the_first_matching_routes_methods() {
    assert_eq!(
        route(&Method::GET, "/api/oauth/cloudflare/claim"),
        Outcome::Matched(Route::Site {
            path: "api/oauth/cloudflare/claim"
        })
    );
    assert_eq!(
        route(&Method::PUT, "/api/oauth/cloudflare/claim"),
        Outcome::NotAllowed("POST")
    );
    assert_eq!(
        route(&Method::POST, "/api/health"),
        Outcome::NotAllowed("GET")
    );
    assert_eq!(
        route(&Method::HEAD, "/api/health"),
        Outcome::NotAllowed("GET")
    );
    assert_eq!(route(&Method::POST, "/"), Outcome::NotAllowed("GET"));
    assert_eq!(route(&Method::DELETE, "/en"), Outcome::NotAllowed("GET"));
}

#[test]
fn python_dollar_also_matches_before_one_final_newline() {
    assert_eq!(
        route(&Method::GET, "/api/health\n"),
        Outcome::Matched(Route::Health)
    );
    assert_eq!(route(&Method::GET, "/\n"), Outcome::Matched(Route::Root));
    assert_eq!(
        route(&Method::GET, "/en\n"),
        Outcome::Matched(Route::Site { path: "en" })
    );
    assert_eq!(
        route(&Method::GET, "/api/health\r"),
        Outcome::Matched(Route::Site {
            path: "api/health\r"
        })
    );
    assert_eq!(route(&Method::GET, "/api/health\n\n"), Outcome::NotFound);
    assert_eq!(route(&Method::GET, "/a\nb"), Outcome::NotFound);
    assert_eq!(route(&Method::HEAD, "/a\nb"), Outcome::NotFound);
}

#[test]
fn the_icon_route_takes_the_longest_icon_name_before_png() {
    let icon = |source, icon| Outcome::Matched(Route::Icon { source, icon });
    assert_eq!(
        route(&Method::GET, "/api/assistant-icons/a/b.png"),
        icon("a", "b")
    );
    assert_eq!(
        route(&Method::GET, "/api/assistant-icons/a/b.png.png"),
        icon("a", "b.png")
    );
    assert_eq!(
        route(&Method::GET, "/api/assistant-icons/a/b.png\n"),
        icon("a", "b")
    );
    assert_eq!(
        route(&Method::GET, "/api/assistant-icons/a\nx/b.png"),
        icon("a\nx", "b")
    );
    for path in [
        "/api/assistant-icons/a/.png",
        "/api/assistant-icons//b.png",
        "/api/assistant-icons/a/b/c.png",
        "/api/assistant-icons/a/b.PNG",
        "/api/assistant-icons/a",
        "/api/assistant-icons/a/b",
    ] {
        assert_eq!(
            route(&Method::GET, path),
            Outcome::Matched(Route::Site { path: &path[1..] }),
            "{path}"
        );
    }
}
