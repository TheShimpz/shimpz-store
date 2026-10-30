//! The TLS a Store serves when given `--tls-certificate` and `--tls-key`: the same dispatcher behind rustls with the
//! ring provider and its safe default protocol versions. Only the UI runner uses it; production terminates TLS at
//! the tunnel connector.

use std::sync::Arc;

use rustls::{
    ServerConfig,
    pki_types::{CertificateDer, PrivateKeyDer, pem::PemObject},
};
use tokio_rustls::TlsAcceptor;

use crate::command::TlsFiles;

/// The certificate chain or key is unreadable or unusable.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct InvalidTlsMaterial;

/// A TLS acceptor over the PEM certificate chain and private key in `files`.
///
/// # Errors
///
/// A file is unreadable, holds no usable PEM item, or the key does not match the certificate.
///
/// # Panics
///
/// Never: the ring provider supports the safe default protocol versions.
pub fn acceptor(files: &TlsFiles) -> Result<TlsAcceptor, InvalidTlsMaterial> {
    let chain = CertificateDer::pem_file_iter(&files.certificate)
        .or(Err(InvalidTlsMaterial))?
        .collect::<Result<Vec<_>, _>>()
        .or(Err(InvalidTlsMaterial))?;
    let key = PrivateKeyDer::from_pem_file(&files.key).or(Err(InvalidTlsMaterial))?;
    let provider = Arc::new(rustls::crypto::ring::default_provider());
    let config = ServerConfig::builder_with_provider(provider)
        .with_safe_default_protocol_versions()
        .expect("the ring provider supports the safe default protocol versions")
        .with_no_client_auth()
        .with_single_cert(chain, key)
        .or(Err(InvalidTlsMaterial))?;
    Ok(TlsAcceptor::from(Arc::new(config)))
}

#[cfg(test)]
mod tests;
