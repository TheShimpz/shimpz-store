use std::{path::Path, sync::Arc, time::Duration};

use rcgen::{CertificateParams, KeyPair};
use rustls::{ClientConfig, RootCertStore, pki_types::ServerName};
use tokio::{
    io::{AsyncReadExt, AsyncWriteExt},
    net::{TcpListener, TcpStream},
    sync::oneshot,
};
use tokio_rustls::TlsConnector;

use super::{InvalidTlsMaterial, acceptor};
use crate::{
    Application,
    command::TlsFiles,
    serve::{Bounds, serve},
};

/// A self-signed certificate for `localhost` and its key, written as PEM files; the certificate's DER.
fn material(directory: &Path) -> (TlsFiles, rustls::pki_types::CertificateDer<'static>) {
    let key = KeyPair::generate().unwrap();
    let certificate = CertificateParams::new(vec!["localhost".to_owned()])
        .unwrap()
        .self_signed(&key)
        .unwrap();
    let files = TlsFiles {
        certificate: directory.join("cert.pem"),
        key: directory.join("key.pem"),
    };
    std::fs::write(&files.certificate, certificate.pem()).unwrap();
    std::fs::write(&files.key, key.serialize_pem()).unwrap();
    (files, certificate.der().clone())
}

#[test]
fn unreadable_or_unusable_material_is_refused() {
    let directory = tempfile::tempdir().unwrap();
    let (files, _) = material(directory.path());
    let other = tempfile::tempdir().unwrap();
    let (other_files, _) = material(other.path());
    let empty = directory.path().join("empty.pem");
    std::fs::write(&empty, "").unwrap();
    let broken = directory.path().join("broken.pem");
    std::fs::write(
        &broken,
        "-----BEGIN CERTIFICATE-----\n!!!!\n-----END CERTIFICATE-----\n",
    )
    .unwrap();
    let missing = directory.path().join("missing.pem");
    for refused in [
        TlsFiles {
            certificate: missing.clone(),
            key: files.key.clone(),
        },
        TlsFiles {
            certificate: broken,
            key: files.key.clone(),
        },
        TlsFiles {
            certificate: files.certificate.clone(),
            key: missing,
        },
        TlsFiles {
            certificate: empty,
            key: files.key.clone(),
        },
        TlsFiles {
            certificate: files.certificate.clone(),
            key: other_files.key,
        },
    ] {
        assert_eq!(
            acceptor(&refused).err(),
            Some(InvalidTlsMaterial),
            "{refused:?}"
        );
    }
}

#[tokio::test]
async fn a_tls_store_serves_the_same_dispatcher_and_drops_a_silent_handshake() {
    let directory = tempfile::tempdir().unwrap();
    let (files, der) = material(directory.path());
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let address = listener.local_addr().unwrap();
    let application = Arc::new(Application::new(&crate::tests::settings()).unwrap());
    let (stop, stopped) = oneshot::channel::<()>();
    let bounds = Bounds {
        header_read_timeout: Duration::from_millis(300),
        shutdown_deadline: Duration::from_secs(1),
    };
    let server = tokio::spawn(serve(
        listener,
        application,
        async move {
            let _ = stopped.await;
        },
        bounds,
        Some(acceptor(&files).unwrap()),
    ));
    let mut roots = RootCertStore::empty();
    roots.add(der).unwrap();
    let provider = Arc::new(rustls::crypto::ring::default_provider());
    let config = ClientConfig::builder_with_provider(provider)
        .with_safe_default_protocol_versions()
        .unwrap()
        .with_root_certificates(roots)
        .with_no_client_auth();
    let stream = TcpStream::connect(address).await.unwrap();
    let mut secured = TlsConnector::from(Arc::new(config))
        .connect(ServerName::try_from("localhost").unwrap(), stream)
        .await
        .unwrap();
    secured
        .write_all(b"GET /api/health HTTP/1.1\r\nHost: s\r\nConnection: close\r\n\r\n")
        .await
        .unwrap();
    let mut answer = Vec::new();
    let _ = secured.read_to_end(&mut answer).await;
    let answer = String::from_utf8(answer).unwrap();
    assert!(answer.starts_with("HTTP/1.1 200 OK\r\n"), "{answer}");
    assert!(answer.ends_with("{\"status\":\"ok\"}"), "{answer}");
    let mut silent = TcpStream::connect(address).await.unwrap();
    let mut buffer = [0; 16];
    let closed = tokio::time::timeout(Duration::from_secs(5), silent.read(&mut buffer))
        .await
        .unwrap();
    assert!(matches!(closed, Ok(0) | Err(_)));
    stop.send(()).unwrap();
    server.await.unwrap();
}
