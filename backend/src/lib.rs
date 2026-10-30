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

use std::{ffi::OsString, net::SocketAddr, process::ExitCode, sync::Arc};

use bytes::Bytes;
use http::{HeaderValue, Method, Request, Response, StatusCode};
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
};

const USAGE: &str = "usage: shimpz-store";

/// One Store: its page policy and the state its routes share.
pub struct Application {
    page_policy: HeaderValue,
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
        })
    }

    /// Answer one request from `peer`, through the security layer.
    pub async fn handle<B>(&self, request: Request<B>, _peer: SocketAddr) -> Response<Full<Bytes>> {
        let path = query::unquote(request.uri().path()).into_owned();
        let id = security::request_id(request.headers());
        let method = request.method().clone();
        let reply = security::guarded(&path, Box::pin(async { dispatch(&method, &path) })).await;
        security::secure(reply, &path, &id, &self.page_policy)
    }
}

/// The reply of the route a request's method and decoded path select.
fn dispatch(method: &Method, path: &str) -> Reply {
    match route::route(method, path) {
        Outcome::Matched(Route::Health) => {
            Reply::json(StatusCode::OK, &b"{\"status\":\"ok\"}"[..], Vec::new())
        }
        Outcome::Matched(_) | Outcome::NotFound => not_found(),
        Outcome::NotAllowed(allow) => not_allowed(allow),
    }
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
