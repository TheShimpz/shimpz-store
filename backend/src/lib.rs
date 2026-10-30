//! The platform Store service (ADR-0123 phase R3): the public site, the Assistant catalog projection, and the
//! Cloudflare OAuth broker, behind one dispatcher that routes as the Python Store did and one security layer.

pub mod config;
pub mod date;
pub mod log;
pub mod policy;
pub mod query;
pub mod response;
pub mod route;
pub mod security;
pub mod serve;
pub mod static_files;

use std::{ffi::OsString, net::SocketAddr, process::ExitCode, sync::Arc};

use bytes::Bytes;
use http::{HeaderMap, HeaderValue, Method, Request, Response, StatusCode, header};
use http_body_util::Full;
use tokio::{
    net::TcpListener,
    signal::unix::{SignalKind, signal},
};

use crate::{
    config::Settings,
    policy::{PolicyError, page_policy},
    response::{Reply, not_allowed, not_found},
    route::{Outcome, Route},
    serve::{Bounds, serve},
    static_files::Site,
};

const USAGE: &str = "usage: shimpz-store";

/// One Store: its page policy and the state its routes share.
pub struct Application {
    page_policy: HeaderValue,
    site: Arc<Site>,
}

impl Application {
    /// The Store for these settings.
    ///
    /// # Errors
    ///
    /// The build admits no page policy.
    pub fn new(settings: &Settings) -> Result<Self, PolicyError> {
        Ok(Self {
            page_policy: page_policy(&settings.build)?,
            site: Arc::new(Site::new(settings.build.clone())),
        })
    }

    /// Answer one request from `peer`, through the security layer.
    pub async fn handle<B>(&self, request: Request<B>, _peer: SocketAddr) -> Response<Full<Bytes>> {
        let path = query::unquote(request.uri().path()).into_owned();
        let id = security::request_id(request.headers());
        let method = request.method().clone();
        let navigation = html_navigation(request.headers());
        let reply =
            security::guarded(&path, Box::pin(self.dispatch(method, &path, navigation))).await;
        security::secure(reply, &path, &id, &self.page_policy)
    }

    /// The reply of the route a request's method and decoded path select.
    async fn dispatch(&self, method: Method, path: &str, navigation: bool) -> Reply {
        match route::route(&method, path) {
            Outcome::Matched(Route::Health) => {
                Reply::json(StatusCode::OK, &b"{\"status\":\"ok\"}"[..], Vec::new())
            }
            Outcome::Matched(Route::Root) => static_files::root_redirect(),
            Outcome::Matched(Route::Site { path }) => {
                let site = Arc::clone(&self.site);
                let path = path.to_owned();
                tokio::task::spawn_blocking(move || site.reply(&path, navigation))
                    .await
                    .expect("a build file read never panics outside the reply")
            }
            Outcome::Matched(_) | Outcome::NotFound => not_found(),
            Outcome::NotAllowed(allow) => not_allowed(allow),
        }
    }
}

/// Whether the request's first `Accept` header names `text/html`, case-insensitively: an HTML navigation.
fn html_navigation(headers: &HeaderMap) -> bool {
    headers.get(header::ACCEPT).is_some_and(|accept| {
        accept
            .as_bytes()
            .to_ascii_lowercase()
            .windows(9)
            .any(|window| window == b"text/html")
    })
}

/// Run the `shimpz-store` command: with no argument, serve until SIGTERM; anything else is a usage error (exit 2).
///
/// # Panics
///
/// When the process cannot start its runtime or install its SIGTERM handler.
#[must_use]
pub fn run(arguments: &[OsString], settings: &Settings) -> ExitCode {
    if !arguments.is_empty() {
        eprintln!("{{\"level\":\"ERROR\",\"msg\":\"{USAGE}\"}}");
        return ExitCode::from(2);
    }
    log::install_panic_hook();
    let Ok(application) = Application::new(settings) else {
        log::event(
            log::Level::Error,
            "startup_failed",
            &[("error", "build_policy_invalid")],
        );
        return ExitCode::FAILURE;
    };
    let runtime = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .expect("the Store runtime starts");
    runtime.block_on(serve_until_terminated(settings, Arc::new(application)))
}

/// Serve until SIGTERM; the signal handler is registered before the listener binds, so a peer that can connect
/// can also stop the Store.
async fn serve_until_terminated(settings: &Settings, application: Arc<Application>) -> ExitCode {
    let mut terminate = signal(SignalKind::terminate()).expect("the SIGTERM handler installs");
    let Ok(listener) = TcpListener::bind(settings.listen).await else {
        log::event(
            log::Level::Error,
            "startup_failed",
            &[("error", "listen_bind_failed")],
        );
        return ExitCode::FAILURE;
    };
    let bounds = Bounds {
        header_read_timeout: settings.header_read_timeout,
        shutdown_deadline: settings.shutdown_deadline,
    };
    serve(
        listener,
        application,
        async move { terminate.recv().await.unwrap_or_default() },
        bounds,
    )
    .await;
    ExitCode::SUCCESS
}

#[cfg(test)]
mod tests;
