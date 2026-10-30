//! The one way Store reaches Neuron: a CONNECT tunnel through Store's closed egress, then TLS to Neuron's name.
//!
//! The egress must answer the CONNECT with exactly `HTTP/1.1 200 Connection established` and an empty line, read in
//! chunks of at most 256 bytes and refused past 1,024 or at EOF. TLS 1.2 or newer verifies Neuron's certificate
//! against the system roots (which honour `SSL_CERT_FILE`, as OpenSSL does for the Python Store). Connecting, every
//! socket operation, and the whole TLS handshake are each bounded by the same timeout.

use std::{sync::Arc, time::Duration};

use rustls::{ClientConfig, RootCertStore, pki_types::ServerName};
use tokio::{
    io::{AsyncRead, AsyncReadExt, AsyncWriteExt},
    net::TcpStream,
};
use tokio_rustls::{TlsConnector, client::TlsStream};

use super::BrokerError;
use crate::catalog::upstream::TimeoutIo;

/// Neuron's host name, the only name the tunnel reaches.
pub const NEURON_HOST: &str = "neuron.shimpz.com";
/// Store's egress on the private network.
pub const EGRESS_HOST: &str = "shimpz-store-egress";
/// The egress port.
pub const EGRESS_PORT: u16 = 8889;
/// The bound on connecting and on each socket operation.
pub const TIMEOUT: Duration = Duration::from_secs(10);
const CONNECT: &[u8] =
    b"CONNECT neuron.shimpz.com:443 HTTP/1.1\r\nHost: neuron.shimpz.com:443\r\n\r\n";
const ESTABLISHED: &[u8] = b"HTTP/1.1 200 Connection established\r\n\r\n";
const MAX_PROXY_RESPONSE_BYTES: usize = 1024;
const PROXY_READ_BYTES: usize = 256;

/// An open TLS stream to Neuron.
pub type NeuronStream = TlsStream<TimeoutIo<TcpStream>>;

/// Where the egress listens and which roots verify Neuron.
#[derive(Clone)]
pub struct Tunnel {
    host: String,
    port: u16,
    timeout: Duration,
    tls: Arc<ClientConfig>,
    name: ServerName<'static>,
}

impl Tunnel {
    /// The deployed Store's tunnel, verifying Neuron against the system roots read now.
    #[must_use]
    pub fn production() -> Self {
        let mut roots = RootCertStore::empty();
        roots.add_parsable_certificates(rustls_native_certs::load_native_certs().certs);
        Self::new(EGRESS_HOST.to_owned(), EGRESS_PORT, TIMEOUT, roots)
    }

    /// A tunnel through the egress at `host:port`, verifying Neuron against `roots`.
    ///
    /// # Panics
    ///
    /// Never: the ring provider supports TLS 1.2 and 1.3, and Neuron's host is a DNS name.
    #[must_use]
    pub fn new(host: String, port: u16, timeout: Duration, roots: RootCertStore) -> Self {
        let provider = Arc::new(rustls::crypto::ring::default_provider());
        let tls = ClientConfig::builder_with_provider(provider)
            .with_protocol_versions(&[&rustls::version::TLS13, &rustls::version::TLS12])
            .expect("the ring provider supports TLS 1.2 and 1.3")
            .with_root_certificates(roots)
            .with_no_client_auth();
        Self {
            host,
            port,
            timeout,
            tls: Arc::new(tls),
            name: ServerName::try_from(NEURON_HOST).expect("Neuron's host is a DNS name"),
        }
    }

    /// Open a verified TLS stream to Neuron through the egress.
    ///
    /// # Errors
    ///
    /// The egress is unreachable or refuses the destination, a socket operation times out, or TLS fails.
    pub async fn open(&self) -> Result<NeuronStream, BrokerError> {
        let connect = tokio::time::timeout(
            self.timeout,
            TcpStream::connect((self.host.as_str(), self.port)),
        );
        let stream = connect.await.or(Err(BrokerError))?.or(Err(BrokerError))?;
        let mut stream = TimeoutIo::new(stream, self.timeout);
        stream.write_all(CONNECT).await.or(Err(BrokerError))?;
        if proxy_response(&mut stream).await? != ESTABLISHED {
            return Err(BrokerError);
        }
        // The whole handshake shares one deadline: per-operation bounds alone would let a peer that drips one byte
        // at a time hold an execution slot indefinitely.
        let handshake =
            TlsConnector::from(Arc::clone(&self.tls)).connect(self.name.clone(), stream);
        tokio::time::timeout(self.timeout, handshake)
            .await
            .or(Err(BrokerError))?
            .or(Err(BrokerError))
    }
}

/// The egress's reply head: read until an empty line, refused at EOF or past 1,024 bytes.
///
/// # Errors
///
/// The stream fails or ends first, or the head grows past 1,024 bytes.
pub async fn proxy_response(
    stream: &mut (dyn AsyncRead + Unpin + Send),
) -> Result<Vec<u8>, BrokerError> {
    let mut reply = Vec::new();
    let mut chunk = [0; PROXY_READ_BYTES];
    while !reply.windows(4).any(|window| window == b"\r\n\r\n") {
        let read = stream.read(&mut chunk).await.or(Err(BrokerError))?;
        if read == 0 {
            return Err(BrokerError);
        }
        reply.extend_from_slice(&chunk[..read]);
        if reply.len() > MAX_PROXY_RESPONSE_BYTES {
            return Err(BrokerError);
        }
    }
    Ok(reply)
}

#[cfg(test)]
mod tests;
