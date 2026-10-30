use std::time::Duration;

use rustls::RootCertStore;
use tokio::{io::AsyncWriteExt, net::TcpListener};

use super::{EGRESS_HOST, EGRESS_PORT, Tunnel};
use crate::oauth::{
    BrokerError,
    testing::{Egress, fake, reply},
};

#[tokio::test]
async fn fixed_transport_uses_exact_connect_proxy_and_end_to_end_neuron_tls() {
    let neuron = fake(Egress::Established, "neuron.shimpz.com", |_| {
        reply("200 OK", "application/json", "{}")
    })
    .await;
    let mut stream = neuron.tunnel.open().await.unwrap();
    stream.write_all(b"GET / HTTP/1.1\r\n\r\n").await.unwrap();
    drop(stream);
    tokio::time::sleep(Duration::from_millis(100)).await;
    let received = neuron.received.lock().unwrap().clone();
    assert_eq!(
        received[0].connect,
        "CONNECT neuron.shimpz.com:443 HTTP/1.1\r\nHost: neuron.shimpz.com:443\r\n\r\n"
    );
}

#[tokio::test]
async fn a_certificate_for_another_name_fails() {
    let neuron = fake(Egress::Established, "other.shimpz.com", |_| Vec::new()).await;
    assert_eq!(neuron.tunnel.open().await.err(), Some(BrokerError));
}

#[tokio::test]
async fn fixed_transport_fails_closed_on_proxy_response() {
    let refusals: [&[u8]; 4] = [
        b"HTTP/1.1 403 Forbidden\r\n\r\n",
        b"HTTP/1.1 200 Connection established\r\nX: y\r\n\r\n",
        b"HTTP/1.1 200 Connection established\r\n",
        &[b'x'; 1025],
    ];
    for bytes in refusals {
        let neuron = fake(Egress::Reply(bytes), "neuron.shimpz.com", |_| Vec::new()).await;
        assert_eq!(
            neuron.tunnel.open().await.err(),
            Some(BrokerError),
            "{bytes:?}"
        );
    }
}

#[tokio::test]
async fn proxy_reader_translates_socket_and_size_failures() {
    let mut long = b"HTTP/1.1 200 Connection established\r\nX: ".to_vec();
    long.resize(1030, b'y');
    long.extend_from_slice(b"\r\n\r\n");
    let bytes: &'static [u8] = Box::leak(long.into_boxed_slice());
    let neuron = fake(Egress::Reply(bytes), "neuron.shimpz.com", |_| Vec::new()).await;
    assert_eq!(neuron.tunnel.open().await.err(), Some(BrokerError));
    let mut failing = Failing;
    assert_eq!(
        super::proxy_response(&mut failing).await.err(),
        Some(BrokerError)
    );
}

/// A reader whose every read fails.
struct Failing;

impl tokio::io::AsyncRead for Failing {
    fn poll_read(
        self: std::pin::Pin<&mut Self>,
        _: &mut std::task::Context<'_>,
        _: &mut tokio::io::ReadBuf<'_>,
    ) -> std::task::Poll<std::io::Result<()>> {
        std::task::Poll::Ready(Err(std::io::Error::other("failed")))
    }
}

#[tokio::test]
async fn neuron_tunnel_translates_connection_failure() {
    let closed = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = closed.local_addr().unwrap().port();
    drop(closed);
    let unreachable = Tunnel::new(
        "127.0.0.1".to_owned(),
        port,
        Duration::from_secs(1),
        RootCertStore::empty(),
    );
    assert_eq!(unreachable.open().await.err(), Some(BrokerError));
    let silent = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = silent.local_addr().unwrap().port();
    let held = tokio::spawn(async move {
        let (stream, _) = silent.accept().await.unwrap();
        tokio::time::sleep(Duration::from_secs(5)).await;
        drop(stream);
    });
    let tunnel = Tunnel::new(
        "127.0.0.1".to_owned(),
        port,
        Duration::from_millis(200),
        RootCertStore::empty(),
    );
    assert_eq!(tunnel.open().await.err(), Some(BrokerError));
    held.abort();
}

#[tokio::test(start_paused = true)]
async fn a_connect_that_never_completes_times_out() {
    let tunnel = Tunnel::new(
        "10.255.255.1".to_owned(),
        9,
        Duration::from_millis(50),
        RootCertStore::empty(),
    );
    assert_eq!(tunnel.open().await.err(), Some(BrokerError));
}

#[test]
fn production_reaches_the_store_egress() {
    let tunnel = Tunnel::production();
    assert_eq!(
        (tunnel.host.as_str(), tunnel.port),
        (EGRESS_HOST, EGRESS_PORT)
    );
    assert_eq!((EGRESS_HOST, EGRESS_PORT), ("shimpz-store-egress", 8889));
    assert_eq!(tunnel.timeout, Duration::from_secs(10));
}
