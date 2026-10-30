//! The platform Store service (ADR-0123 phase R3): the public site, the Assistant catalog projection, and the
//! Cloudflare OAuth broker, behind one dispatcher that routes as the Python Store did and one security layer.

pub mod catalog;
pub mod clock;
pub mod command;
pub mod config;
pub mod date;
pub mod healthcheck;
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
pub mod tls;

use std::{ffi::OsString, net::SocketAddr, process::ExitCode, sync::Arc};

use bytes::Bytes;
use http::{HeaderMap, HeaderValue, Request, Response, StatusCode, header};
use http_body_util::BodyExt;
use http_body_util::Full;
use tokio::{
    net::TcpListener,
    signal::unix::{SignalKind, signal},
};
use tokio_rustls::TlsAcceptor;

use crate::{
    catalog::Catalog,
    clock::Clock,
    clock::SystemClock,
    command::{Command, TlsFiles},
    config::Settings,
    oauth::{
        body::Body,
        broker::Broker,
        routes::{Oauth, Post},
    },
    policy::page_policy,
    ratelimit::{StartLimit, trusted_proxies},
    response::{Reply, not_allowed, not_found},
    route::{Outcome, Route},
    serve::{Bounds, serve},
    static_files::Site,
};

/// One Store: its page policy and the state its routes share.
pub struct Application {
    page_policy: HeaderValue,
    site: Arc<Site>,
    catalog: Catalog,
    oauth: Oauth,
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
        let clock: Arc<dyn Clock> = Arc::new(SystemClock::new());
        Self::assemble(settings, Arc::clone(&clock), Broker::production(clock))
    }

    /// The Store for these settings on `clock`, with this OAuth broker.
    ///
    /// # Errors
    ///
    /// The trusted proxy networks are invalid, or the build admits no page policy.
    pub fn assemble(
        settings: &Settings,
        clock: Arc<dyn Clock>,
        broker: Broker,
    ) -> Result<Self, StartupError> {
        let proxies = trusted_proxies(settings.trusted_proxies.as_deref())
            .or(Err(StartupError::TrustedProxiesInvalid))?;
        let policy = page_policy(&settings.build).or(Err(StartupError::BuildPolicyInvalid))?;
        Ok(Self {
            page_policy: policy,
            site: Arc::new(Site::new(settings.build.clone())),
            catalog: Catalog::new(
                &settings.developers,
                Arc::clone(&clock),
                settings.developers_slot_wait,
            ),
            oauth: Oauth::new(broker, StartLimit::new(proxies, clock)),
        })
    }

    /// The OAuth broker's routes.
    #[must_use]
    pub fn oauth(&self) -> &Oauth {
        &self.oauth
    }

    /// Answer one request from `peer`, through the security layer.
    pub async fn handle<B>(&self, request: Request<B>, peer: SocketAddr) -> Response<Full<Bytes>>
    where
        B: hyper::body::Body<Data = Bytes> + Send + 'static,
        B::Error: Into<oauth::body::BodyError>,
    {
        let request = request.map(|body| body.map_err(Into::into).boxed_unsync());
        self.respond(request, peer).await
    }

    async fn respond(&self, request: Request<Body>, peer: SocketAddr) -> Response<Full<Bytes>> {
        let path = query::unquote(request.uri().path()).into_owned();
        let id = security::request_id(request.headers());
        let dispatched = self.dispatch(request, &path, peer);
        let reply = security::guarded(&path, dispatched).await;
        security::secure(reply, &path, &id, &self.page_policy)
    }

    /// The reply of the route a request's method and decoded path select.
    async fn dispatch(&self, request: Request<Body>, path: &str, peer: SocketAddr) -> Reply {
        let (parts, body) = request.into_parts();
        let query = parts.uri.query();
        let navigation = html_navigation(&parts.headers);
        match route::route(&parts.method, path) {
            Outcome::Matched(Route::Start) => {
                self.oauth
                    .start(peer.ip(), &parts.headers, query, path)
                    .await
            }
            Outcome::Matched(Route::Callback) => self.oauth.callback(query, path).await,
            Outcome::Matched(Route::Claim) => {
                self.oauth
                    .post(Post::Claim, &parts.headers, body, path)
                    .await
            }
            Outcome::Matched(Route::Refresh) => {
                self.oauth
                    .post(Post::Refresh, &parts.headers, body, path)
                    .await
            }
            Outcome::Matched(Route::Revoke) => {
                self.oauth
                    .post(Post::Revoke, &parts.headers, body, path)
                    .await
            }
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
            Outcome::NotFound => not_found(),
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

/// Run the `shimpz-store` command ([`command`]): serve until SIGTERM, plainly or over TLS, or check the local
/// Store's health (exit 0 when healthy, 1 otherwise); any other command line is a usage error (exit 2).
///
/// # Panics
///
/// When the process cannot start its runtime or install its SIGTERM handler.
#[must_use]
pub fn run(arguments: &[OsString], settings: &Settings) -> ExitCode {
    let tls = match command::parse(arguments) {
        None => {
            eprintln!("{{\"level\":\"ERROR\",\"msg\":\"{}\"}}", command::USAGE);
            return ExitCode::from(2);
        }
        Some(Command::Healthcheck) => {
            return if healthcheck::healthy(settings.listen.port()) {
                ExitCode::SUCCESS
            } else {
                ExitCode::FAILURE
            };
        }
        Some(Command::Serve(tls)) => tls,
    };
    log::install_panic_hook();
    match start(settings, tls.as_ref()) {
        Ok((application, acceptor)) => {
            let runtime = tokio::runtime::Builder::new_multi_thread()
                .enable_all()
                .build()
                .expect("the Store runtime starts");
            runtime.block_on(serve_until_terminated(
                settings,
                Arc::new(application),
                acceptor,
            ))
        }
        Err(code) => {
            log::event(log::Level::Error, "startup_failed", &[("error", code)]);
            ExitCode::FAILURE
        }
    }
}

/// The application and, when TLS files are given, its acceptor; or the closed code of the startup refusal.
fn start(
    settings: &Settings,
    tls: Option<&TlsFiles>,
) -> Result<(Application, Option<TlsAcceptor>), &'static str> {
    let application = Application::new(settings).map_err(StartupError::code)?;
    let acceptor = tls
        .map(tls::acceptor)
        .transpose()
        .or(Err("tls_material_invalid"))?;
    Ok((application, acceptor))
}

/// Serve until SIGTERM; the signal handler is registered before the listener binds, so a peer that can connect
/// can also stop the Store.
async fn serve_until_terminated(
    settings: &Settings,
    application: Arc<Application>,
    tls: Option<TlsAcceptor>,
) -> ExitCode {
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
        tls,
    )
    .await;
    ExitCode::SUCCESS
}

#[cfg(test)]
mod tests;
