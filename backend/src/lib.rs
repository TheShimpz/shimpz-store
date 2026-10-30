//! The platform Store service (ADR-0123 phase R3): the public site, the Assistant catalog projection, and the
//! Cloudflare OAuth broker, behind one dispatcher that routes as the Python Store did and one security layer.

pub mod catalog;
pub mod clock;
pub mod config;
pub mod date;
pub mod log;
pub mod oauth;
pub mod policy;
pub mod query;
pub mod ratelimit;
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
    catalog::Catalog,
    clock::SystemClock,
    config::Settings,
    policy::page_policy,
    ratelimit::{StartLimit, StartRefusal, trusted_proxies},
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
    catalog: Catalog,
    start_limit: StartLimit,
}

/// Why the Store refused to start.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum StartupError {
    /// `SHIMPZ_STORE_TRUSTED_PROXY_CIDRS` is not a list of exact networks.
    TrustedProxiesInvalid,
    /// The build admits no page policy.
    BuildPolicyInvalid,
}

impl StartupError {
    /// The closed code the refusal is logged with.
    #[must_use]
    pub fn code(self) -> &'static str {
        match self {
            Self::TrustedProxiesInvalid => "trusted_proxies_invalid",
            Self::BuildPolicyInvalid => "build_policy_invalid",
        }
    }
}

impl Application {
    /// The Store for these settings.
    ///
    /// # Errors
    ///
    /// The trusted proxy networks are invalid, or the build admits no page policy.
    pub fn new(settings: &Settings) -> Result<Self, StartupError> {
        let proxies = trusted_proxies(settings.trusted_proxies.as_deref())
            .or(Err(StartupError::TrustedProxiesInvalid))?;
        let policy = page_policy(&settings.build).or(Err(StartupError::BuildPolicyInvalid))?;
        let clock = Arc::new(SystemClock::new());
        Ok(Self {
            page_policy: policy,
            site: Arc::new(Site::new(settings.build.clone())),
            catalog: Catalog::new(
                &settings.developers,
                clock.clone(),
                settings.developers_slot_wait,
            ),
            start_limit: StartLimit::new(proxies, clock),
        })
    }

    /// Count one OAuth start from `peer` against its client: `None` when admitted, otherwise the refusal.
    #[must_use]
    pub fn admit_start(&self, peer: SocketAddr, headers: &HeaderMap) -> Option<Reply> {
        let refusal = self.start_limit.admit(peer.ip(), headers).err()?;
        let (status, extra) = match refusal {
            StartRefusal::ClientAddress => (StatusCode::BAD_REQUEST, None),
            StartRefusal::Limited(seconds) => (
                StatusCode::TOO_MANY_REQUESTS,
                Some((header::RETRY_AFTER, HeaderValue::from(seconds))),
            ),
        };
        Some(oauth::failure("start", status, extra))
    }

    /// Answer one request from `peer`, through the security layer.
    pub async fn handle<B>(&self, request: Request<B>, _peer: SocketAddr) -> Response<Full<Bytes>> {
        let path = query::unquote(request.uri().path()).into_owned();
        let id = security::request_id(request.headers());
        let method = request.method().clone();
        let navigation = html_navigation(request.headers());
        let raw_query = request.uri().query().map(str::to_owned);
        let dispatched = self.dispatch(method, &path, raw_query.as_deref(), navigation);
        let reply = security::guarded(&path, Box::pin(dispatched)).await;
        security::secure(reply, &path, &id, &self.page_policy)
    }

    /// The reply of the route a request's method and decoded path select.
    async fn dispatch(
        &self,
        method: Method,
        path: &str,
        query: Option<&str>,
        navigation: bool,
    ) -> Reply {
        match route::route(&method, path) {
            Outcome::Matched(Route::Health) => {
                Reply::json(StatusCode::OK, &b"{\"status\":\"ok\"}"[..], Vec::new())
            }
            Outcome::Matched(Route::Root) => static_files::root_redirect(),
            Outcome::Matched(Route::Catalog) => self.catalog.catalog(query).await,
            Outcome::Matched(Route::Icon { source, icon }) => self.catalog.icon(source, icon).await,
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
    let application = match Application::new(settings) {
        Ok(application) => application,
        Err(refusal) => {
            log::event(
                log::Level::Error,
                "startup_failed",
                &[("error", refusal.code())],
            );
            return ExitCode::FAILURE;
        }
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
