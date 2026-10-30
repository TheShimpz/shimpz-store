//! The HTTP/1.1 accept loop: every connection must deliver each request head within a bound, carries its peer
//! address to the application, and is drained on shutdown within one deadline, after which it is aborted.

use std::{future::Future, io, net::SocketAddr, pin::pin, sync::Arc, time::Duration};

use futures_util::future::{Either, select};
use hyper::{body::Incoming, server::conn::http1, service::service_fn};
use hyper_util::{
    rt::{TokioIo, TokioTimer},
    server::graceful::GracefulShutdown,
};
use tokio::{
    net::{TcpListener, TcpStream},
    task::JoinSet,
};

use crate::Application;

/// How long accepting pauses after a listener error other than a peer's aborted connection, such as running out of
/// file descriptors, so the loop does not spin.
const ACCEPT_ERROR_PAUSE: Duration = Duration::from_secs(1);
/// The most header fields one request head may carry.
const MAX_HEADERS: usize = 100;
/// The largest request head, start line included, in bytes; a larger one is answered 431 and closed.
const MAX_HEAD_BYTES: usize = 64 * 1024;

/// A source of accepted connections.
pub trait Accept: Send {
    /// The accepted connection.
    type Stream: tokio::io::AsyncRead + tokio::io::AsyncWrite + Unpin + Send + 'static;

    /// The next connection and its peer address.
    fn accept(&mut self) -> impl Future<Output = io::Result<(Self::Stream, SocketAddr)>> + Send;
}

impl Accept for TcpListener {
    type Stream = TcpStream;

    fn accept(&mut self) -> impl Future<Output = io::Result<(TcpStream, SocketAddr)>> + Send {
        TcpListener::accept(self)
    }
}

/// The two bounds of serving: one request head, and the drain after shutdown.
#[derive(Clone, Copy, Debug)]
pub struct Bounds {
    /// The longest a connection may take to deliver a complete request head.
    pub header_read_timeout: Duration,
    /// The longest connections may take to finish after shutdown before they are aborted.
    pub shutdown_deadline: Duration,
}

/// Serve `application` on `acceptor` until `shutdown` completes; then stop accepting, ask every connection to
/// finish its in-flight request, and abort whatever remains at the deadline.
pub async fn serve<A: Accept>(
    mut acceptor: A,
    application: Arc<Application>,
    shutdown: impl Future<Output = ()>,
    bounds: Bounds,
) {
    let graceful = GracefulShutdown::new();
    let mut connections = JoinSet::new();
    let mut shutdown = pin!(shutdown);
    loop {
        let accepted = match select(pin!(acceptor.accept()), &mut shutdown).await {
            Either::Left((accepted, _)) => accepted,
            Either::Right(((), _)) => break,
        };
        while connections.try_join_next().is_some() {}
        match accepted {
            Ok((stream, peer)) => {
                let application = Arc::clone(&application);
                let service = service_fn(move |request: http::Request<Incoming>| {
                    let application = Arc::clone(&application);
                    async move {
                        Ok::<_, std::convert::Infallible>(application.handle(request, peer).await)
                    }
                });
                let connection = http1::Builder::new()
                    .timer(TokioTimer::new())
                    .header_read_timeout(bounds.header_read_timeout)
                    .max_headers(MAX_HEADERS)
                    .max_header_size(MAX_HEAD_BYTES)
                    .serve_connection(TokioIo::new(stream), service);
                let connection = graceful.watch(connection);
                connections.spawn(async move {
                    // A failed or timed-out connection concerns only its own peer.
                    let _ended = connection.await;
                });
            }
            Err(error) => pause_after_accept_error(&error).await,
        }
    }
    drop(acceptor);
    drain(graceful, connections, bounds.shutdown_deadline).await;
}

/// Let connections finish until the deadline, then abort the rest and wait until every one has ended.
async fn drain(graceful: GracefulShutdown, mut connections: JoinSet<()>, deadline: Duration) {
    if tokio::time::timeout(deadline, graceful.shutdown())
        .await
        .is_err()
    {
        connections.abort_all();
    }
    while connections.join_next().await.is_some() {}
}

async fn pause_after_accept_error(error: &io::Error) {
    if matches!(
        error.kind(),
        io::ErrorKind::ConnectionRefused
            | io::ErrorKind::ConnectionAborted
            | io::ErrorKind::ConnectionReset
    ) {
        return;
    }
    crate::log::event(
        crate::log::Level::Error,
        "accept_failed",
        &[("error", "listen_accept_failed")],
    );
    tokio::time::sleep(ACCEPT_ERROR_PAUSE).await;
}

#[cfg(test)]
mod tests;
