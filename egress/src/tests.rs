use std::fs;
use std::io::{Read, Write};
use std::net::TcpListener;
use std::os::unix::fs::PermissionsExt;
use std::path::PathBuf;
use std::time::Duration;

use egress_transport::audit::SystemDisk;
use egress_transport::fixtures::{
    FixedStamp, client_hello, exchange, pair, public, read_all, transport,
};
use egress_transport::handler::handle;
use egress_transport::{AuditWriter, Decision, Envelope, Fields, Outcome, Profile, Target, refuse};

use super::{EXACT_REQUEST, LIMITS, PORT, SERVICE, Setup, Startup, Store, event, run, start};

/// A private 0700 directory removed at drop.
struct Scratch(PathBuf);

impl Scratch {
    fn new(name: &str) -> Self {
        let path = std::env::temp_dir().join(format!("store-egress-{name}-{}", std::process::id()));
        let _ = fs::remove_dir_all(&path);
        fs::create_dir(&path).expect("scratch");
        fs::set_permissions(&path, fs::Permissions::from_mode(0o700)).expect("mode");
        Self(path)
    }

    fn writer(&self) -> AuditWriter {
        AuditWriter::with_parts(
            self.0.join("audit.jsonl"),
            SERVICE,
            Box::new(FixedStamp::default()),
            Box::new(SystemDisk),
        )
    }

    fn lines(&self) -> Vec<String> {
        fs::read_to_string(self.0.join("audit.jsonl"))
            .unwrap_or_default()
            .lines()
            .map(str::to_owned)
            .collect()
    }
}

impl Drop for Scratch {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

#[test]
fn the_wire_contract_and_envelope_are_pinned() {
    let scratch = Scratch::new("pinned");
    let store = Store::new(scratch.writer());
    assert_eq!(
        EXACT_REQUEST,
        b"CONNECT neuron.shimpz.com:443 HTTP/1.1\r\nHost: neuron.shimpz.com:443\r\n\r\n"
    );
    let envelope = Envelope {
        connect_timeout: Duration::from_secs(10),
        idle_timeout: Duration::from_secs(30),
        request_limit: 1024,
        challenge: "",
    };
    assert_eq!(store.envelope(), envelope);
    assert_eq!(
        (
            LIMITS.concurrency,
            LIMITS.source_concurrency,
            LIMITS.backlog
        ),
        (8, 8, 8)
    );
    assert_eq!(PORT, 8889);
}

#[test]
fn admission_requires_the_exact_complete_connect_request() {
    let scratch = Scratch::new("exact");
    let store = Store::new(scratch.writer());
    let client = public("172.20.0.2:1").ip();
    assert_eq!(
        store.admit(EXACT_REQUEST, client),
        Ok(Target::new("neuron.shimpz.com", 443))
    );
    let mut trailing = EXACT_REQUEST.to_vec();
    trailing.extend_from_slice(b"\x16\x03\x01");
    let with_secret = String::from_utf8_lossy(EXACT_REQUEST)
        .replace("\r\n\r\n", "\r\nProxy-Authorization: secret\r\n\r\n");
    for payload in [
        b"GET https://neuron.shimpz.com/ HTTP/1.1\r\n\r\n".to_vec(),
        b"CONNECT neuron.shimpz.com:443 HTTP/1.0\r\n\r\n".to_vec(),
        String::from_utf8_lossy(EXACT_REQUEST)
            .replace("443", "80")
            .into_bytes(),
        with_secret.into_bytes(),
        trailing,
    ] {
        assert_eq!(
            store.admit(&payload, client),
            Err(refuse(
                400,
                "request-rejected",
                "rejected-target",
                Fields::new()
            ))
        );
    }
}

#[test]
fn a_client_hello_naming_neuron_is_relayed_after_one_recorded_admission() {
    let scratch = Scratch::new("relay");
    let store = Store::new(scratch.writer());
    let upstream = TcpListener::bind("127.0.0.1:0").expect("bind");
    let (transport, _) = transport(
        vec![public("1.1.1.1:443")],
        upstream.local_addr().expect("address"),
        Vec::new(),
    );
    let (server, mut client) = pair();
    let worker =
        std::thread::spawn(move || handle(&store, &transport, server, public("172.20.0.2:1")));
    client.write_all(EXACT_REQUEST).expect("request");
    let mut status = [0u8; 39];
    client.read_exact(&mut status).expect("200");
    let flight = client_hello("neuron.shimpz.com");
    client.write_all(&flight).expect("hello");
    let (mut neuron, _) = upstream.accept().expect("upstream");
    neuron
        .set_read_timeout(Some(Duration::from_secs(10)))
        .expect("timeout");
    let mut received = vec![0u8; flight.len()];
    neuron.read_exact(&mut received).expect("relayed");
    assert_eq!(received, flight);
    drop(client);
    worker.join().expect("handled");
    let lines = scratch.lines();
    assert_eq!(lines.len(), 1);
    assert!(lines[0].starts_with(
        "{\"code\":200,\"operation\":\"connect\",\"prev_sha256\":\"0000000000000000000000000000000000000000000000000000000000000000\",\
         \"principal_class\":\"machine\",\"principal_id\":\"store\",\"reason\":\"allowed\",\"result\":\"ok\",\
         \"service\":\"store-egress\",\"subject\":\"neuron.shimpz.com:443\""
    ));
    let mode = fs::metadata(scratch.0.join("audit.jsonl"))
        .expect("audit")
        .permissions()
        .mode();
    assert_eq!(mode & 0o777, 0o600);
}

#[test]
fn a_fronted_server_name_and_a_wrong_request_are_recorded_without_request_material() {
    let scratch = Scratch::new("fronted");
    let store = Store::new(scratch.writer());
    let upstream = TcpListener::bind("127.0.0.1:0").expect("bind");
    let (transport, _) = transport(
        vec![public("1.1.1.1:443")],
        upstream.local_addr().expect("address"),
        Vec::new(),
    );
    let (server, mut client) = pair();
    client.write_all(EXACT_REQUEST).expect("request");
    let worker = std::thread::spawn(move || {
        handle(&store, &transport, server, public("172.20.0.2:1"));
        (store, transport)
    });
    let mut status = [0u8; 39];
    client.read_exact(&mut status).expect("200");
    client
        .write_all(&client_hello("example.com"))
        .expect("hello");
    assert_eq!(read_all(&mut client), b"");
    let (store, transport) = worker.join().expect("handled");
    let secret = String::from_utf8_lossy(EXACT_REQUEST)
        .replace("\r\n\r\n", "\r\nProxy-Authorization: secret\r\n\r\n");
    let response = exchange(
        &store,
        &transport,
        secret.as_bytes(),
        public("172.20.0.2:1"),
    );
    assert!(response.starts_with(b"HTTP/1.1 400"));
    let lines = scratch.lines();
    assert!(
        lines[1].contains("\"reason\":\"sni-mismatch\"")
            && lines[1].contains("\"subject\":\"neuron.shimpz.com:443\"")
    );
    assert!(lines[2].contains("\"subject\":\"rejected-target\""));
    assert!(!lines.join("\n").contains("secret"));
}

#[test]
fn the_audit_admits_only_its_bounded_schema() {
    for subject in ["attacker.example:443", "not-evaluated"] {
        let decision = Decision {
            result: Outcome::Ok,
            ..refuse(200, "allowed", subject, Fields::new())
        };
        assert!(event(&decision).is_err());
    }
}

fn setup(scratch: &Scratch, port: u16) -> Setup {
    let (transport, _) = transport(Vec::new(), public("127.0.0.1:9"), Vec::new());
    Setup {
        audit: scratch.writer(),
        port,
        transport,
    }
}

#[test]
fn startup_checks_custody_then_binds_and_serves() {
    let scratch = Scratch::new("startup");
    let server = start(setup(&scratch, 0)).expect("starts");
    let busy = server.listener.local_addr().expect("address").port();
    assert_eq!(start(setup(&scratch, busy)).err(), Some(Startup::Listen));
    fs::set_permissions(&scratch.0, fs::Permissions::from_mode(0o750)).expect("mode");
    assert_eq!(start(setup(&scratch, 0)).err(), Some(Startup::Custody));
    assert_eq!(run(setup(&scratch, 0)), 1);
    fs::set_permissions(&scratch.0, fs::Permissions::from_mode(0o700)).expect("mode");
    assert_eq!(
        Startup::Custody.to_string(),
        "audit custody is unavailable; refusing to start"
    );
    assert_eq!(
        Startup::Listen.to_string(),
        "the listener is unavailable; refusing to start"
    );
    let port = TcpListener::bind("127.0.0.1:0")
        .expect("bind")
        .local_addr()
        .expect("address")
        .port();
    let serving = setup(&scratch, port);
    std::thread::spawn(move || run(serving));
    let deadline = std::time::Instant::now() + Duration::from_secs(5);
    while !egress_transport::health::listening(port, Duration::from_secs(1)) {
        assert!(
            std::time::Instant::now() < deadline,
            "the profile never listened"
        );
        std::thread::sleep(Duration::from_millis(20));
    }
    assert_eq!(super::main(), 1);
}
