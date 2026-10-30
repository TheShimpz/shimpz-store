use std::{
    io,
    net::SocketAddr,
    sync::Arc,
    time::{Duration, Instant},
};

use tokio::{
    io::{AsyncReadExt, AsyncWriteExt, DuplexStream, duplex},
    net::{TcpListener, TcpStream},
    sync::oneshot,
    task::JoinHandle,
};

use hyper_util::server::graceful::GracefulShutdown;
use tokio::task::JoinSet;

use super::{Accept, Bounds, drain, serve};
use crate::Application;

fn application() -> Arc<Application> {
    Arc::new(Application::new(&crate::tests::settings()).unwrap())
}

fn bounds(header: u64, deadline: u64) -> Bounds {
    Bounds {
        header_read_timeout: Duration::from_millis(header),
        shutdown_deadline: Duration::from_millis(deadline),
    }
}

async fn started(bounds: Bounds) -> (SocketAddr, oneshot::Sender<()>, JoinHandle<()>) {
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let address = listener.local_addr().unwrap();
    let (stop, stopped) = oneshot::channel::<()>();
    let server = tokio::spawn(serve(
        listener,
        application(),
        async move {
            let _ = stopped.await;
        },
        bounds,
    ));
    (address, stop, server)
}

async fn get(address: SocketAddr, head: &[u8]) -> String {
    let mut client = TcpStream::connect(address).await.unwrap();
    client.write_all(head).await.unwrap();
    let mut answer = Vec::new();
    client.read_to_end(&mut answer).await.unwrap();
    String::from_utf8(answer).unwrap()
}

#[tokio::test]
async fn connections_are_served_one_after_another_and_shutdown_ends_the_loop() {
    let (address, stop, server) = started(bounds(10_000, 1_000)).await;
    for _ in 0..3 {
        let answer = get(
            address,
            b"GET /api/health HTTP/1.1\r\nHost: s\r\nConnection: close\r\n\r\n",
        )
        .await;
        assert!(answer.starts_with("HTTP/1.1 200 OK\r\n"), "{answer}");
        assert!(answer.ends_with("{\"status\":\"ok\"}"), "{answer}");
    }
    stop.send(()).unwrap();
    server.await.unwrap();
}

#[tokio::test]
async fn a_head_answer_carries_no_body() {
    let (address, _stop, _server) = started(bounds(10_000, 1_000)).await;
    let answer = get(
        address,
        b"HEAD /api/health HTTP/1.1\r\nHost: s\r\nConnection: close\r\n\r\n",
    )
    .await;
    assert!(
        answer.starts_with("HTTP/1.1 405 Method Not Allowed\r\n"),
        "{answer}"
    );
    assert!(answer.contains("\r\ncontent-length: 31\r\n"), "{answer}");
    assert!(answer.ends_with("\r\n\r\n"), "{answer}");
}

#[tokio::test]
async fn a_client_sending_its_head_slowly_is_disconnected() {
    let (address, _stop, _server) = started(bounds(200, 1_000)).await;
    let mut client = TcpStream::connect(address).await.unwrap();
    client
        .write_all(b"GET /api/health HTTP/1.1\r\n")
        .await
        .unwrap();
    let started = Instant::now();
    let mut answer = Vec::new();
    client.read_to_end(&mut answer).await.unwrap();
    assert!(started.elapsed() < Duration::from_secs(5));
    assert!(!String::from_utf8_lossy(&answer).contains("200 OK"));
}

#[tokio::test]
async fn an_oversized_or_overfull_head_is_refused_before_the_application() {
    let (address, _stop, _server) = started(bounds(10_000, 1_000)).await;
    let big = [
        b"GET / HTTP/1.1\r\nX-Big: ".as_slice(),
        &vec![b'b'; 70_000],
        b"\r\n\r\n",
    ]
    .concat();
    let many: Vec<u8> = (0..150)
        .flat_map(|index| format!("X-{index}: 1\r\n").into_bytes())
        .collect();
    let crowded = [b"GET / HTTP/1.1\r\nHost: s\r\n".as_slice(), &many, b"\r\n"].concat();
    for (label, head) in [("big", big), ("crowded", crowded)] {
        let answer = get(address, &head).await;
        assert!(
            answer.starts_with("HTTP/1.1 4") && !answer.contains("x-request-id"),
            "{label}: {answer}"
        );
        assert!(!answer.contains("x-request-id"), "{answer}");
    }
}

#[tokio::test]
async fn a_connection_still_answering_at_the_deadline_is_aborted() {
    let (mut client, server_side) = duplex(4096);
    let service = hyper::service::service_fn(|_request: http::Request<hyper::body::Incoming>| {
        std::future::pending::<
            Result<http::Response<http_body_util::Full<bytes::Bytes>>, std::convert::Infallible>,
        >()
    });
    let graceful = GracefulShutdown::new();
    let connection = graceful.watch(
        hyper::server::conn::http1::Builder::new()
            .serve_connection(hyper_util::rt::TokioIo::new(server_side), service),
    );
    let mut connections = JoinSet::new();
    connections.spawn(async move {
        let _ended = connection.await;
    });
    client
        .write_all(b"GET /api/health HTTP/1.1\r\nHost: s\r\n\r\n")
        .await
        .unwrap();
    tokio::time::sleep(Duration::from_millis(50)).await;
    let started = Instant::now();
    drain(
        graceful,
        connections,
        &application(),
        Duration::from_millis(200),
    )
    .await;
    assert!(started.elapsed() >= Duration::from_millis(200));
    assert!(started.elapsed() < Duration::from_secs(5));
}

/// An acceptor that yields scripted results, then stays pending.
struct Scripted(Vec<io::Result<(DuplexStream, SocketAddr)>>);

impl Accept for Scripted {
    type Stream = DuplexStream;

    async fn accept(&mut self) -> io::Result<(DuplexStream, SocketAddr)> {
        match self.0.pop() {
            Some(result) => result,
            None => std::future::pending().await,
        }
    }
}

#[tokio::test(start_paused = true)]
async fn an_aborted_accept_is_skipped_and_another_failure_pauses_the_loop() {
    let (client, server_side) = duplex(4096);
    let peer = SocketAddr::from(([127, 0, 0, 1], 9));
    let script = Scripted(vec![
        Ok((server_side, peer)),
        Err(io::Error::from(io::ErrorKind::OutOfMemory)),
        Err(io::Error::from(io::ErrorKind::ConnectionAborted)),
        Err(io::Error::from(io::ErrorKind::ConnectionReset)),
        Err(io::Error::from(io::ErrorKind::ConnectionRefused)),
    ]);
    let (stop, stopped) = oneshot::channel::<()>();
    let server = tokio::spawn(serve(
        script,
        application(),
        async move { stopped.await.unwrap() },
        bounds(1_000, 1_000),
    ));
    let mut client = client;
    client
        .write_all(b"GET /api/health HTTP/1.1\r\nHost: s\r\nConnection: close\r\n\r\n")
        .await
        .unwrap();
    let mut answer = Vec::new();
    client.read_to_end(&mut answer).await.unwrap();
    assert!(String::from_utf8_lossy(&answer).starts_with("HTTP/1.1 200 OK"));
    stop.send(()).unwrap();
    server.await.unwrap();
}
