//! The one shutdown deadline over connections and owned broker operations.

use std::{
    net::SocketAddr,
    sync::Arc,
    time::{Duration, Instant},
};

use tokio::{
    io::{AsyncReadExt, AsyncWriteExt},
    net::{TcpListener, TcpStream},
    sync::oneshot,
    task::JoinHandle,
};

use super::{Bounds, serve};
use crate::{
    Application,
    oauth::{
        broker::challenge_of,
        testing::{Fake, broker, neuron_answer},
    },
};

const DEADLINE: Duration = Duration::from_secs(1);

async fn served() -> (
    Fake,
    Arc<Application>,
    SocketAddr,
    oneshot::Sender<()>,
    JoinHandle<()>,
) {
    let (fake, broker, clock) = broker(neuron_answer).await;
    let application =
        Arc::new(Application::assemble(&crate::tests::settings(), clock, broker).unwrap());
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let address = listener.local_addr().unwrap();
    let (stop, stopped) = oneshot::channel::<()>();
    let bounds = Bounds {
        header_read_timeout: Duration::from_secs(10),
        shutdown_deadline: DEADLINE,
    };
    let server = tokio::spawn(serve(
        listener,
        Arc::clone(&application),
        async move {
            let _ = stopped.await;
        },
        bounds,
        None,
    ));
    (fake, application, address, stop, server)
}

fn start_request() -> String {
    format!(
        "GET /api/oauth/cloudflare/start?state={}&code_challenge={}&scope=dns.read&callback=loopback HTTP/1.1\r\n\
         Host: s\r\nConnection: close\r\n\r\n",
        "s".repeat(43),
        challenge_of(&"v".repeat(43))
    )
}

async fn held_start(fake: &Fake, address: SocketAddr) -> TcpStream {
    fake.held.send_replace(true);
    let mut client = TcpStream::connect(address).await.unwrap();
    client.write_all(start_request().as_bytes()).await.unwrap();
    while fake.received.lock().unwrap().is_empty() {
        tokio::time::sleep(Duration::from_millis(5)).await;
    }
    client
}

#[tokio::test]
async fn shutdown_aborts_a_stalled_request_body_at_the_deadline() {
    let (_fake, application, address, stop, server) = served().await;
    let mut client = TcpStream::connect(address).await.unwrap();
    client
        .write_all(
            b"POST /api/oauth/cloudflare/revoke HTTP/1.1\r\nHost: s\r\nContent-Type: application/json\r\n\
              Content-Length: 10\r\n\r\n{\"",
        )
        .await
        .unwrap();
    tokio::time::sleep(Duration::from_millis(50)).await;
    let started = Instant::now();
    stop.send(()).unwrap();
    server.await.unwrap();
    assert!(started.elapsed() >= DEADLINE);
    assert!(started.elapsed() < DEADLINE + Duration::from_secs(1));
    assert!(application.oauth().idle());
}

#[tokio::test]
async fn shutdown_aborts_a_held_neuron_operation_at_the_deadline_with_clean_guards() {
    let (fake, application, address, stop, server) = served().await;
    let _client = held_start(&fake, address).await;
    assert!(!application.oauth().idle());
    let started = Instant::now();
    stop.send(()).unwrap();
    server.await.unwrap();
    assert!(started.elapsed() >= DEADLINE);
    assert!(started.elapsed() < DEADLINE + Duration::from_secs(1));
    assert!(
        application.oauth().idle(),
        "the aborted start released its authorization and local state"
    );
}

#[tokio::test]
async fn shutdown_waits_for_owned_operations_that_end_before_the_deadline() {
    let (fake, application, address, stop, server) = served().await;
    let mut client = held_start(&fake, address).await;
    let started = Instant::now();
    stop.send(()).unwrap();
    tokio::time::sleep(Duration::from_millis(100)).await;
    fake.held.send_replace(false);
    let mut answer = Vec::new();
    client.read_to_end(&mut answer).await.unwrap();
    server.await.unwrap();
    assert!(started.elapsed() < DEADLINE);
    assert!(String::from_utf8_lossy(&answer).starts_with("HTTP/1.1 303 See Other\r\n"));
    assert!(
        !application.oauth().idle(),
        "the completed start keeps its pending authorization"
    );
}
