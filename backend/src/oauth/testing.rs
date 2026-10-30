//! A scripted Store egress with Neuron behind it, for the tunnel and Neuron client tests: a CA and a leaf for a
//! chosen name are generated at test time, so no key is committed.

use std::{
    path::PathBuf,
    sync::{Arc, Mutex},
    time::Duration,
};

use rcgen::{BasicConstraints, CertificateParams, IsCa, Issuer, KeyPair};
use rustls::{
    RootCertStore, ServerConfig,
    pki_types::{CertificateDer, PrivateKeyDer, PrivatePkcs8KeyDer},
};
use tokio::{
    io::{AsyncRead, AsyncReadExt, AsyncWriteExt},
    net::TcpListener,
};
use tokio_rustls::TlsAcceptor;

use super::{secret::tests::installed, tunnel::Tunnel};

/// What the scripted egress does with a CONNECT.
#[derive(Clone, Copy)]
pub enum Egress {
    /// Establish the tunnel to the scripted Neuron.
    Established,
    /// Answer these bytes and close.
    Reply(&'static [u8]),
}

/// One request Neuron received: the CONNECT head, the request head, and the body.
#[derive(Clone, Debug, Default)]
pub struct Recorded {
    /// The CONNECT request head the egress read.
    pub connect: String,
    /// The HTTP request head Neuron read.
    pub head: String,
    /// The request body.
    pub body: String,
}

type Script = Arc<dyn Fn(&Recorded) -> Vec<u8> + Send + Sync>;

/// The scripted egress and Neuron, the tunnel and credential that reach them, and what they received.
pub struct Fake {
    /// A tunnel through the scripted egress that trusts the scripted Neuron's CA.
    pub tunnel: Tunnel,
    /// A valid Access credential's two files.
    pub credential: [PathBuf; 2],
    /// Every request Neuron received.
    pub received: Arc<Mutex<Vec<Recorded>>>,
    /// While true, Neuron holds every answer after recording its request.
    pub held: tokio::sync::watch::Sender<bool>,
    /// The temporary directory holding the credential and any key files.
    pub directory: tempfile::TempDir,
}

/// A JSON reply with this status line and body.
pub fn reply(status: &str, content_type: &str, body: &str) -> Vec<u8> {
    format!(
        "HTTP/1.1 {status}\r\nContent-Type: {content_type}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
        body.len()
    )
    .into_bytes()
}

/// A server presenting a leaf for `name` signed by a fresh CA, and roots holding only that CA.
fn certificates(name: &str) -> (ServerConfig, RootCertStore) {
    let ca_key = KeyPair::generate().unwrap();
    let mut ca_params = CertificateParams::new(Vec::<String>::new()).unwrap();
    ca_params.is_ca = IsCa::Ca(BasicConstraints::Unconstrained);
    let ca = ca_params.self_signed(&ca_key).unwrap();
    let leaf_key = KeyPair::generate().unwrap();
    let leaf = CertificateParams::new(vec![name.to_owned()])
        .unwrap()
        .signed_by(&leaf_key, &Issuer::from_params(&ca_params, &ca_key))
        .unwrap();
    let provider = Arc::new(rustls::crypto::ring::default_provider());
    let server = ServerConfig::builder_with_provider(provider)
        .with_safe_default_protocol_versions()
        .unwrap()
        .with_no_client_auth()
        .with_single_cert(
            vec![CertificateDer::from(leaf.der().to_vec())],
            PrivateKeyDer::Pkcs8(PrivatePkcs8KeyDer::from(leaf_key.serialize_der())),
        )
        .unwrap();
    let mut roots = RootCertStore::empty();
    roots.add(ca.der().clone()).unwrap();
    (server, roots)
}

/// A scripted egress and a Neuron presenting a certificate for `name`, answering every request with `script`.
pub async fn fake(
    egress: Egress,
    name: &str,
    script: impl Fn(&Recorded) -> Vec<u8> + Send + Sync + 'static,
) -> Fake {
    let (server, roots) = certificates(name);
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = listener.local_addr().unwrap().port();
    let received = Arc::new(Mutex::new(Vec::new()));
    let script: Script = Arc::new(script);
    let (held, gate) = tokio::sync::watch::channel(false);
    tokio::spawn(serve(
        listener,
        egress,
        TlsAcceptor::from(Arc::new(server)),
        script,
        (Arc::clone(&received), gate),
    ));
    let directory = tempfile::tempdir().unwrap();
    let credential = [
        installed(
            directory.path(),
            "access-client-id",
            b"client-id-0000000.access",
        ),
        installed(
            directory.path(),
            "access-client-secret",
            "s".repeat(32).as_bytes(),
        ),
    ];
    Fake {
        tunnel: Tunnel::new("127.0.0.1".to_owned(), port, Duration::from_secs(5), roots),
        credential,
        received,
        held,
        directory,
    }
}

async fn serve(
    listener: TcpListener,
    egress: Egress,
    acceptor: TlsAcceptor,
    script: Script,
    (received, gate): (
        Arc<Mutex<Vec<Recorded>>>,
        tokio::sync::watch::Receiver<bool>,
    ),
) {
    loop {
        let (mut stream, _) = listener.accept().await.unwrap();
        let (acceptor, script, received, mut gate) = (
            acceptor.clone(),
            Arc::clone(&script),
            Arc::clone(&received),
            gate.clone(),
        );
        tokio::spawn(async move {
            let connect = head(&mut stream).await;
            let Egress::Established = egress else {
                if let Egress::Reply(bytes) = egress {
                    let _ = stream.write_all(bytes).await;
                }
                return;
            };
            stream
                .write_all(b"HTTP/1.1 200 Connection established\r\n\r\n")
                .await
                .unwrap();
            let Ok(mut secured) = acceptor.accept(stream).await else {
                return;
            };
            let request_head = head(&mut secured).await;
            let length = request_head
                .lines()
                .find_map(|line| line.strip_prefix("content-length: "))
                .map_or(0, |length| length.parse().unwrap());
            let mut body = vec![0; length];
            secured.read_exact(&mut body).await.unwrap();
            let recorded = Recorded {
                connect,
                head: request_head,
                body: String::from_utf8(body).unwrap(),
            };
            let answer = script(&recorded);
            received.lock().unwrap().push(recorded);
            let _ = gate.wait_for(|held| !*held).await;
            let _ = secured.write_all(&answer).await;
            let _ = secured.shutdown().await;
        });
    }
}

/// Read one head, byte by byte, up to its empty line.
async fn head(stream: &mut (impl AsyncRead + Unpin)) -> String {
    let mut head = Vec::new();
    while !head.ends_with(b"\r\n\r\n") {
        let mut byte = [0; 1];
        if stream.read(&mut byte).await.unwrap_or(0) == 0 {
            break;
        }
        head.push(byte[0]);
    }
    String::from_utf8_lossy(&head).into_owned()
}

/// Neuron's answer to a well-formed call: the consent URL echoing its state and challenge, tokens for its scopes
/// (`access-token-0001`, `refresh-token-001`, an hour), or the revoke acknowledgement.
pub fn neuron_answer(recorded: &Recorded) -> Vec<u8> {
    let body = strict_json::parse(recorded.body.as_bytes()).unwrap();
    let text = |name: &str| match body.get(name) {
        Some(strict_json::Value::String(text)) => text.clone(),
        _ => String::new(),
    };
    let scopes = match body.get("scopes") {
        Some(strict_json::Value::Array(items)) => items
            .iter()
            .map(|item| match item {
                strict_json::Value::String(text) => format!("\"{text}\""),
                _ => String::new(),
            })
            .collect::<Vec<_>>(),
        _ => Vec::new(),
    };
    let path = recorded.head.split(' ').nth(1).unwrap_or_default();
    let json = match path.rsplit('/').next().unwrap_or_default() {
        "authorization" => format!(
            "{{\"authorization_url\":\"https://dash.cloudflare.com/oauth2/auth?response_type=code&client_id=client-1\
             &redirect_uri=https://shimpz.com/api/oauth/cloudflare/callback&state={}&code_challenge={}\
             &code_challenge_method=S256&scope={}\"}}",
            text("state"),
            text("code_challenge"),
            scopes.join(" ").replace('"', "").replace(' ', "+")
        ),
        "revoke" => String::from("{\"revoked\":true}"),
        _ => format!(
            "{{\"access_token\":\"access-token-0001\",\"refresh_token\":\"refresh-token-001\",\
             \"scopes\":[{}],\"expires_in\":3600}}",
            scopes.join(",")
        ),
    };
    reply("200 OK", "application/json", &json)
}

/// The broker state and PKCE challenge of the latest authorization Neuron received.
pub fn latest_authorization(fake: &Fake) -> (String, String) {
    let received = fake.received.lock().unwrap();
    let recorded = received
        .iter()
        .rev()
        .find(|recorded| recorded.head.contains("/authorization "))
        .unwrap();
    let body = strict_json::parse(recorded.body.as_bytes()).unwrap();
    let text = |name: &str| match body.get(name) {
        Some(strict_json::Value::String(text)) => text.clone(),
        _ => String::new(),
    };
    (text("state"), text("code_challenge"))
}

/// A broker over a scripted Neuron, lease keys in a temporary directory, and a manual clock at wall second
/// 1,800,000,000.
pub async fn broker(
    script: impl Fn(&Recorded) -> Vec<u8> + Send + Sync + 'static,
) -> (Fake, super::broker::Broker, Arc<crate::clock::ManualClock>) {
    let fake = fake(Egress::Established, "neuron.shimpz.com", script).await;
    let clock = Arc::new(crate::clock::ManualClock::at(1_800_000_000));
    let keys = [
        installed(fake.directory.path(), "lease-key", &[b'n'; 32]),
        installed(fake.directory.path(), "lease-key-previous", &[b'q'; 32]),
    ];
    let neuron = super::neuron::Neuron::new(fake.tunnel.clone(), fake.credential.clone());
    let signer = super::lease::LeaseSigner::new(keys, clock.clone());
    let broker = super::broker::Broker::new(neuron, signer, clock.clone());
    (fake, broker, clock)
}
