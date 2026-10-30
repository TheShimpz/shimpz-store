use std::{sync::Arc, time::Duration};

use tokio::{
    io::{AsyncReadExt, AsyncWriteExt, duplex},
    net::TcpListener,
    sync::Mutex,
};

use super::{Developers, Failure, TimeoutIo, log_failure};

/// What a scripted Developers does with one connection after it read the request head.
#[derive(Clone, Copy)]
enum Script {
    Reply(&'static [u8]),
    ReplyThenStall(&'static [u8]),
    Stall,
}

/// A one-connection Developers that records the request head it received.
async fn scripted(script: Script) -> (Developers, Arc<Mutex<String>>) {
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = listener.local_addr().unwrap().port();
    let head = Arc::new(Mutex::new(String::new()));
    let recorded = Arc::clone(&head);
    tokio::spawn(async move {
        let (mut stream, _) = listener.accept().await.unwrap();
        let mut buffer = vec![0; 4096];
        let read = stream.read(&mut buffer).await.unwrap();
        *recorded.lock().await = String::from_utf8_lossy(&buffer[..read]).into_owned();
        match script {
            Script::Reply(reply) => stream.write_all(reply).await.unwrap(),
            Script::ReplyThenStall(reply) => {
                stream.write_all(reply).await.unwrap();
                std::future::pending::<()>().await;
            }
            Script::Stall => std::future::pending::<()>().await,
        }
    });
    let developers = Developers {
        host: "127.0.0.1".into(),
        port,
        timeout: Duration::from_secs(5),
    };
    (developers, head)
}

#[tokio::test]
async fn a_read_sends_one_closed_request_and_returns_the_status_headers_and_body() {
    let (developers, head) = scripted(Script::Reply(
        b"HTTP/1.1 200 OK\r\nContent-Type: image/png; x=1\r\nContent-Type: text/html\r\nContent-Length: 3\r\n\r\npng",
    ))
    .await;
    let fetched = developers
        .get("/api/v1/x?locale=en", Some("image/png"), 16)
        .await
        .unwrap();
    assert_eq!(fetched.status, http::StatusCode::OK);
    assert_eq!(
        fetched.content_type.as_deref(),
        Some("image/png; x=1, text/html")
    );
    assert_eq!(fetched.content_length.as_deref(), Some("3"));
    assert_eq!(fetched.body.as_deref(), Some(&b"png"[..]));
    let head = head.lock().await.to_ascii_lowercase();
    assert!(
        head.starts_with("get /api/v1/x?locale=en http/1.1\r\n"),
        "{head}"
    );
    for line in [
        "host: 127.0.0.1:",
        "accept-encoding: identity\r\n",
        "accept: image/png\r\n",
    ] {
        assert!(head.contains(line), "{head}");
    }
}

#[tokio::test]
async fn a_body_past_the_bound_is_marked_too_long_and_absent_headers_are_none() {
    let (developers, head) = scripted(Script::Reply(
        b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n12345",
    ))
    .await;
    let fetched = developers.get("/x", None, 4).await.unwrap();
    assert_eq!(fetched.status, http::StatusCode::NOT_FOUND);
    assert_eq!(
        (fetched.content_type, fetched.content_length, fetched.body),
        (None, None, None)
    );
    assert!(!head.lock().await.to_ascii_lowercase().contains("accept:"));
}

#[tokio::test]
async fn framing_failures_and_a_broken_body_are_protocol_errors() {
    for reply in [
        &b"NOT HTTP\r\n\r\n"[..],
        b"HTTP/1.1 200 OK\r\nContent-Length: 10\r\n\r\n12",
    ] {
        let (developers, _head) = scripted(Script::Reply(reply)).await;
        assert_eq!(
            developers.get("/x", None, 64).await.unwrap_err(),
            Failure::Protocol
        );
    }
}

#[tokio::test]
async fn an_unreachable_developers_fails_to_connect() {
    let port = TcpListener::bind("127.0.0.1:0")
        .await
        .unwrap()
        .local_addr()
        .unwrap()
        .port();
    let developers = Developers {
        host: "127.0.0.1".into(),
        port,
        timeout: Duration::from_secs(5),
    };
    assert_eq!(
        developers.get("/x", None, 64).await.unwrap_err(),
        Failure::Connect
    );
    let nowhere = Developers {
        host: "nowhere.invalid".into(),
        port,
        timeout: Duration::from_secs(5),
    };
    assert_eq!(
        nowhere.get("/x", None, 64).await.unwrap_err(),
        Failure::Connect
    );
}

#[tokio::test(start_paused = true)]
async fn a_connection_that_never_completes_times_out() {
    let developers = Developers {
        host: "10.255.255.1".into(),
        port: 9,
        timeout: Duration::from_secs(5),
    };
    assert_eq!(
        developers.get("/x", None, 64).await.unwrap_err(),
        Failure::Connect
    );
}

#[tokio::test(start_paused = true)]
async fn a_silent_head_or_a_stalled_body_times_out() {
    let (developers, _head) = scripted(Script::Stall).await;
    assert_eq!(
        developers.get("/x", None, 64).await.unwrap_err(),
        Failure::TimedOut
    );
    let (developers, _head) = scripted(Script::ReplyThenStall(
        b"HTTP/1.1 200 OK\r\nContent-Length: 10\r\n\r\n12",
    ))
    .await;
    assert_eq!(
        developers.get("/x", None, 64).await.unwrap_err(),
        Failure::TimedOut
    );
}

#[tokio::test(start_paused = true)]
async fn a_write_that_never_drains_times_out_and_flush_and_shutdown_pass_through() {
    let (client, _server) = duplex(8);
    let mut bounded = TimeoutIo::new(client, Duration::from_secs(5));
    let error = bounded.write_all(&[0; 64]).await.unwrap_err();
    assert_eq!(error.kind(), std::io::ErrorKind::TimedOut);
    bounded.flush().await.unwrap();
    bounded.shutdown().await.unwrap();
}

#[test]
fn every_failure_has_a_closed_code() {
    assert_eq!(Failure::Connect.code(), "connect_failed");
    assert_eq!(Failure::TimedOut.code(), "timed_out");
    assert_eq!(Failure::Protocol.code(), "protocol_error");
    log_failure(
        "proxy_unreachable",
        "/api/v1/assistants?locale=en",
        Failure::TimedOut,
    );
}
