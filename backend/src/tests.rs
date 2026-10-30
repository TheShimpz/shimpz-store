use std::{
    io::{Read, Write},
    net::{SocketAddr, TcpListener, TcpStream},
    path::PathBuf,
    process::ExitCode,
    time::{Duration, Instant},
};

use http::{Method, Request, StatusCode};
use http_body_util::BodyExt;

use super::{Application, StartupError, run};
use crate::config::Settings;

/// Settings on a free loopback port and a build directory that does not exist.
pub(crate) fn settings() -> Settings {
    let port = TcpListener::bind("127.0.0.1:0")
        .unwrap()
        .local_addr()
        .unwrap()
        .port();
    Settings {
        listen: SocketAddr::from(([127, 0, 0, 1], port)),
        build: PathBuf::from("/nonexistent/store-build"),
        header_read_timeout: Duration::from_secs(10),
        shutdown_deadline: Duration::from_secs(1),
        developers: crate::catalog::upstream::Developers {
            host: "127.0.0.1".into(),
            port,
            timeout: Duration::from_secs(5),
        },
        developers_slot_wait: Duration::from_secs(5),
        trusted_proxies: None,
    }
}

async fn answer(
    application: &Application,
    method: Method,
    target: &str,
    accept: &str,
) -> (StatusCode, String) {
    let request = Request::builder()
        .method(method)
        .uri(target)
        .header("accept", accept)
        .body(http_body_util::Empty::<bytes::Bytes>::new())
        .unwrap();
    let response = application
        .handle(request, SocketAddr::from(([127, 0, 0, 1], 9)))
        .await;
    let status = response.status();
    let body = response.into_body().collect().await.unwrap().to_bytes();
    (status, String::from_utf8(body.to_vec()).unwrap())
}

/// A page whose build policy names no script, as the not-found pages carry.
const PAGE: &str = "<meta http-equiv=\"content-security-policy\" content=\"script-src 'self'; \
                    require-trusted-types-for 'script'; trusted-types svelte-trusted-html\">";

fn site_application() -> (tempfile::TempDir, Application) {
    let build = tempfile::tempdir().unwrap();
    std::fs::write(build.path().join("en.html"), format!("{PAGE}english-home")).unwrap();
    std::fs::create_dir(build.path().join("en")).unwrap();
    std::fs::write(
        build.path().join("en/404.html"),
        format!("{PAGE}english-not-found"),
    )
    .unwrap();
    let settings = Settings {
        build: build.path().to_path_buf(),
        ..settings()
    };
    let application = Application::new(&settings).unwrap();
    (build, application)
}

#[tokio::test]
async fn the_dispatcher_answers_health_refusals_and_misses_through_the_security_layer() {
    let (_build, application) = site_application();
    let ok = (StatusCode::OK, String::from("{\"status\":\"ok\"}"));
    assert_eq!(
        answer(&application, Method::GET, "/api/health?x=1", "").await,
        ok
    );
    assert_eq!(
        answer(&application, Method::GET, "/api/health%0a", "").await,
        ok
    );
    assert_eq!(
        answer(&application, Method::POST, "/api/health", "").await,
        (
            StatusCode::METHOD_NOT_ALLOWED,
            "{\"detail\":\"Method Not Allowed\"}".into()
        )
    );
    assert_eq!(
        answer(&application, Method::GET, "/a%0Ab", "").await,
        (StatusCode::NOT_FOUND, "{\"detail\":\"Not Found\"}".into())
    );
    let start = answer(&application, Method::GET, "/api/oauth/cloudflare/start", "").await;
    assert_eq!(start.0, StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn the_dispatcher_serves_the_root_redirect_pages_and_localized_misses() {
    let (_build, application) = site_application();
    for method in [Method::GET, Method::HEAD] {
        assert_eq!(
            answer(&application, method, "/", "").await.0,
            StatusCode::PERMANENT_REDIRECT
        );
    }
    let page = answer(&application, Method::GET, "/%65n", "").await;
    assert!(
        page.0 == StatusCode::OK && page.1.ends_with("english-home"),
        "{page:?}"
    );
    let navigation = answer(&application, Method::GET, "/missing", "TEXT/HTML").await;
    assert!(
        navigation.0 == StatusCode::NOT_FOUND && navigation.1.ends_with("english-not-found"),
        "{navigation:?}"
    );
    assert_eq!(
        answer(&application, Method::GET, "/missing", "application/json").await,
        (StatusCode::NOT_FOUND, "not found".into())
    );
}

#[test]
fn any_argument_is_a_usage_error() {
    assert_eq!(run(&["serve".into()], &settings()), ExitCode::from(2));
}

#[test]
fn the_healthcheck_command_reports_the_local_stores_health() {
    let settings = settings();
    assert_eq!(run(&["healthcheck".into()], &settings), ExitCode::FAILURE);
    let runtime = tokio::runtime::Runtime::new().unwrap();
    let listener = runtime
        .block_on(tokio::net::TcpListener::bind(settings.listen))
        .unwrap();
    let application = std::sync::Arc::new(Application::new(&settings).unwrap());
    let bounds = crate::serve::Bounds {
        header_read_timeout: Duration::from_secs(10),
        shutdown_deadline: Duration::from_secs(1),
    };
    let (stop, stopped) = tokio::sync::oneshot::channel::<()>();
    let server = runtime.spawn(crate::serve::serve(
        listener,
        application,
        async move {
            let _ = stopped.await;
        },
        bounds,
        None,
    ));
    assert_eq!(run(&["healthcheck".into()], &settings), ExitCode::SUCCESS);
    stop.send(()).unwrap();
    runtime.block_on(server).unwrap();
}

#[test]
fn tls_material_is_read_before_serving_and_refuses_to_start_when_unusable() {
    let directory = tempfile::tempdir().unwrap();
    let missing = directory.path().join("missing.pem");
    let arguments: Vec<std::ffi::OsString> = vec![
        "--tls-certificate".into(),
        missing.clone().into(),
        "--tls-key".into(),
        missing.into(),
    ];
    assert_eq!(run(&arguments, &settings()), ExitCode::FAILURE);
    let key = rcgen::KeyPair::generate().unwrap();
    let certificate = rcgen::CertificateParams::new(vec!["localhost".to_owned()])
        .unwrap()
        .self_signed(&key)
        .unwrap();
    let files = crate::command::TlsFiles {
        certificate: directory.path().join("cert.pem"),
        key: directory.path().join("key.pem"),
    };
    std::fs::write(&files.certificate, certificate.pem()).unwrap();
    std::fs::write(&files.key, key.serialize_pem()).unwrap();
    let (_, acceptor) = super::start(&settings(), Some(&files)).unwrap();
    assert!(acceptor.is_some());
    let (_, plain) = super::start(&settings(), None).unwrap();
    assert!(plain.is_none());
}

#[test]
fn a_build_without_an_exact_policy_refuses_to_start() {
    let build = tempfile::tempdir().unwrap();
    std::fs::write(build.path().join("en.html"), "<script>x()</script>").unwrap();
    let settings = Settings {
        build: build.path().to_path_buf(),
        ..settings()
    };
    assert_eq!(run(&[], &settings), ExitCode::FAILURE);
    assert_eq!(
        Application::new(&settings).err(),
        Some(StartupError::BuildPolicyInvalid)
    );
    assert_eq!(
        StartupError::BuildPolicyInvalid.code(),
        "build_policy_invalid"
    );
}

#[test]
fn invalid_trusted_proxies_refuse_to_start() {
    let settings = Settings {
        trusted_proxies: Some("10.0.0.1/24".into()),
        ..settings()
    };
    assert_eq!(run(&[], &settings), ExitCode::FAILURE);
    assert_eq!(
        Application::new(&settings).err(),
        Some(StartupError::TrustedProxiesInvalid)
    );
    assert_eq!(
        StartupError::TrustedProxiesInvalid.code(),
        "trusted_proxies_invalid"
    );
}

#[test]
fn an_oauth_start_is_counted_against_its_client_and_refused_without_a_usable_address() {
    let settings = Settings {
        trusted_proxies: Some("10.0.0.0/24".into()),
        ..settings()
    };
    let application = Application::new(&settings).unwrap();
    let direct = SocketAddr::from(([192, 0, 2, 1], 40_000));
    for _ in 0..10 {
        assert!(
            application
                .oauth()
                .admit_start(direct.ip(), &http::HeaderMap::new())
                .is_none()
        );
    }
    let limited = application
        .oauth()
        .admit_start(direct.ip(), &http::HeaderMap::new())
        .unwrap();
    assert_eq!(limited.status, StatusCode::TOO_MANY_REQUESTS);
    assert_eq!(limited.header(&http::header::RETRY_AFTER).unwrap(), "6");
    let proxy = SocketAddr::from(([10, 0, 0, 2], 40_000));
    let refused = application
        .oauth()
        .admit_start(proxy.ip(), &http::HeaderMap::new())
        .unwrap();
    assert_eq!(refused.status, StatusCode::BAD_REQUEST);
    assert_eq!(refused.header(&http::header::RETRY_AFTER), None);
}

#[test]
fn a_taken_address_refuses_to_start() {
    let taken = TcpListener::bind("127.0.0.1:0").unwrap();
    let settings = Settings {
        listen: taken.local_addr().unwrap(),
        ..settings()
    };
    assert_eq!(run(&[], &settings), ExitCode::FAILURE);
}

#[test]
fn the_store_serves_until_sigterm_and_then_exits_cleanly() {
    let settings = settings();
    let address = settings.listen;
    let server = std::thread::spawn(move || run(&[], &settings));
    let deadline = Instant::now() + Duration::from_secs(30);
    let mut stream = loop {
        match TcpStream::connect(address) {
            Ok(stream) => break stream,
            Err(_) if Instant::now() < deadline => std::thread::sleep(Duration::from_millis(20)),
            Err(error) => panic!("the Store never listened: {error}"),
        }
    };
    stream
        .write_all(b"GET /api/health HTTP/1.1\r\nHost: s\r\nConnection: close\r\n\r\n")
        .unwrap();
    let mut answer = String::new();
    stream.read_to_string(&mut answer).unwrap();
    assert!(answer.starts_with("HTTP/1.1 200 OK\r\n"), "{answer}");
    rustix::process::kill_process(rustix::process::getpid(), rustix::process::Signal::TERM)
        .unwrap();
    assert_eq!(server.join().unwrap(), ExitCode::SUCCESS);
}

#[tokio::test]
async fn the_dispatcher_sends_each_oauth_route_to_the_broker() {
    let (_build, application) = site_application();
    let callback = answer(
        &application,
        Method::GET,
        "/api/oauth/cloudflare/callback",
        "*/*",
    )
    .await;
    assert_eq!(callback.0, StatusCode::BAD_REQUEST);
    for operation in ["claim", "refresh", "revoke"] {
        let target = format!("/api/oauth/cloudflare/{operation}");
        let refused = answer(&application, Method::POST, &target, "*/*").await;
        assert_eq!(refused.0, StatusCode::FORBIDDEN, "{operation}");
    }
}

#[tokio::test]
async fn the_dispatcher_sends_catalog_and_icon_requests_to_the_catalog() {
    let (_build, application) = site_application();
    let refused = answer(
        &application,
        Method::GET,
        "/api/assistants?locale=xx",
        "*/*",
    )
    .await;
    assert_eq!(refused.0, StatusCode::BAD_REQUEST);
    let icon = answer(
        &application,
        Method::GET,
        "/api/assistant-icons/a/b.png",
        "*/*",
    )
    .await;
    assert_eq!(icon.0, StatusCode::SERVICE_UNAVAILABLE);
}

#[tokio::test]
async fn health() {
    let (_build, application) = site_application();
    assert_eq!(
        answer(&application, Method::GET, "/api/health", "").await,
        (StatusCode::OK, String::from("{\"status\":\"ok\"}"))
    );
}
