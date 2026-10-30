//! Bounded one-hop reads from Developers: one HTTP/1.1 request per connection, each socket operation (connect, every
//! read, every write) bounded by the same timeout, as the Python Store's `http.client` socket timeout bounded it.

use std::{
    future::Future,
    io,
    pin::Pin,
    task::{Context, Poll, ready},
    time::Duration,
};

use bytes::Bytes;
use http::{HeaderValue, Request, StatusCode, header};
use http_body_util::{BodyExt, Empty, Limited};
use hyper::client::conn::http1;
use hyper_util::rt::TokioIo;
use tokio::{
    io::{AsyncRead, AsyncWrite, ReadBuf},
    net::TcpStream,
    time::{Sleep, sleep},
};

use crate::log::{Level, event};

/// The largest JSON document read from Developers.
pub const MAX_JSON_BYTES: usize = 4 * 1024 * 1024;
/// The largest asset read from Developers.
pub const MAX_ASSET_BYTES: usize = 1024 * 1024;

/// Where Developers listens and how long each socket operation may take.
#[derive(Clone, Debug)]
pub struct Developers {
    /// Developers' host name on the private network.
    pub host: String,
    /// Developers' port.
    pub port: u16,
    /// The bound on connecting and on each read and write.
    pub timeout: Duration,
}

/// One reply Developers gave: its status, the headers the caller reads, and its body within the bound.
#[derive(Debug)]
pub struct Fetched {
    /// The status.
    pub status: StatusCode,
    /// Every `Content-Type` value, joined by `", "` as `http.client` joins repeated headers.
    pub content_type: Option<String>,
    /// Every `Content-Length` value, joined the same way.
    pub content_length: Option<String>,
    /// The body, or `None` when it was longer than the read bound.
    pub body: Option<Bytes>,
}

/// Why a read failed before Developers answered completely; each is a closed log code.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Failure {
    /// The connection could not be made in time.
    Connect,
    /// A read or write ran out of time.
    TimedOut,
    /// Developers' reply was not HTTP/1.1 Store can read, or the connection broke.
    Protocol,
}

impl Failure {
    /// The closed code a log line names.
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Connect => "connect_failed",
            Self::TimedOut => "timed_out",
            Self::Protocol => "protocol_error",
        }
    }
}

impl Developers {
    /// `GET path` with `accept`, reading at most `limit` body bytes (one more marks the body as too long).
    ///
    /// # Errors
    ///
    /// The connection, a socket operation, or HTTP/1.1 framing failed.
    pub async fn get(
        &self,
        path: &str,
        accept: Option<&'static str>,
        limit: usize,
    ) -> Result<Fetched, Failure> {
        let connect = tokio::time::timeout(
            self.timeout,
            TcpStream::connect((self.host.as_str(), self.port)),
        );
        let stream = connect
            .await
            .or(Err(Failure::Connect))?
            .or(Err(Failure::Connect))?;
        let io = TokioIo::new(TimeoutIo::new(stream, self.timeout));
        let (mut sender, connection) = http1::handshake(io).await.or(Err(Failure::Protocol))?;
        tokio::spawn(connection);
        let authority = format!("{}:{}", self.host, self.port);
        let mut request = Request::get(path)
            .header(header::HOST, authority)
            .header(header::ACCEPT_ENCODING, "identity");
        if let Some(accept) = accept {
            request = request.header(header::ACCEPT, accept);
        }
        let request = request
            .body(Empty::<Bytes>::new())
            .or(Err(Failure::Protocol))?;
        let response = sender
            .send_request(request)
            .await
            .map_err(|error| boxed_failure(&error))?;
        let joined = |name: header::HeaderName| joined(response.headers().get_all(name).iter());
        let (content_type, content_length) =
            (joined(header::CONTENT_TYPE), joined(header::CONTENT_LENGTH));
        let status = response.status();
        let body = match Limited::new(response.into_body(), limit).collect().await {
            Ok(collected) => Some(collected.to_bytes()),
            Err(error) if error.is::<http_body_util::LengthLimitError>() => None,
            Err(error) => return Err(boxed_failure(&*error)),
        };
        Ok(Fetched {
            status,
            content_type,
            content_length,
            body,
        })
    }
}

/// Log a failed read by its closed code and the path, whose only query is a validated locale.
pub fn log_failure(code: &str, path: &str, failure: Failure) {
    event(
        Level::Warning,
        code,
        &[("path", path), ("error", failure.code())],
    );
}

fn joined<'a>(values: impl Iterator<Item = &'a HeaderValue>) -> Option<String> {
    let values: Vec<String> = values
        .map(|value| {
            value
                .as_bytes()
                .iter()
                .map(|byte| char::from(*byte))
                .collect()
        })
        .collect();
    (!values.is_empty()).then(|| values.join(", "))
}

/// A timed-out socket operation, wherever hyper wrapped it, or any other failure as a protocol error.
fn boxed_failure(error: &(dyn std::error::Error + 'static)) -> Failure {
    let mut source = Some(error);
    while let Some(current) = source {
        if current
            .downcast_ref::<io::Error>()
            .is_some_and(|io| io.kind() == io::ErrorKind::TimedOut)
        {
            return Failure::TimedOut;
        }
        source = current.source();
    }
    Failure::Protocol
}

/// A stream whose every read and write must make progress within `timeout`.
pub struct TimeoutIo<S> {
    inner: S,
    timeout: Duration,
    read: Option<Pin<Box<Sleep>>>,
    write: Option<Pin<Box<Sleep>>>,
}

impl<S> TimeoutIo<S> {
    /// Bound each operation on `inner` by `timeout`.
    pub const fn new(inner: S, timeout: Duration) -> Self {
        Self {
            inner,
            timeout,
            read: None,
            write: None,
        }
    }
}

/// Poll one operation under its own deadline, started at its first pending poll and cleared when it completes.
fn bounded<T>(
    deadline: &mut Option<Pin<Box<Sleep>>>,
    timeout: Duration,
    context: &mut Context<'_>,
    operation: Poll<io::Result<T>>,
) -> Poll<io::Result<T>> {
    if operation.is_ready() {
        *deadline = None;
        return operation;
    }
    let timer = deadline.get_or_insert_with(|| Box::pin(sleep(timeout)));
    ready!(timer.as_mut().poll(context));
    *deadline = None;
    Poll::Ready(Err(io::Error::from(io::ErrorKind::TimedOut)))
}

impl<S: AsyncRead + Unpin> AsyncRead for TimeoutIo<S> {
    fn poll_read(
        mut self: Pin<&mut Self>,
        context: &mut Context<'_>,
        buffer: &mut ReadBuf<'_>,
    ) -> Poll<io::Result<()>> {
        let this = &mut *self;
        let operation = Pin::new(&mut this.inner).poll_read(context, buffer);
        bounded(&mut this.read, this.timeout, context, operation)
    }
}

impl<S: AsyncWrite + Unpin> AsyncWrite for TimeoutIo<S> {
    fn poll_write(
        mut self: Pin<&mut Self>,
        context: &mut Context<'_>,
        data: &[u8],
    ) -> Poll<io::Result<usize>> {
        let this = &mut *self;
        let operation = Pin::new(&mut this.inner).poll_write(context, data);
        bounded(&mut this.write, this.timeout, context, operation)
    }

    fn poll_flush(mut self: Pin<&mut Self>, context: &mut Context<'_>) -> Poll<io::Result<()>> {
        Pin::new(&mut self.inner).poll_flush(context)
    }

    fn poll_shutdown(mut self: Pin<&mut Self>, context: &mut Context<'_>) -> Poll<io::Result<()>> {
        Pin::new(&mut self.inner).poll_shutdown(context)
    }
}

#[cfg(test)]
mod tests;
