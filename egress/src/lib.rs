//! CONNECT-only outbound enforcement from the platform Store to private Neuron (`shimpz-egress store`).
//!
//! The Store process and this proxy share one internal network; only the proxy joins an outbound network. It admits
//! exactly one request, `CONNECT neuron.shimpz.com:443`, and records a bounded decision before any upstream connection
//! attempt. TLS and Cloudflare Access authentication stay end to end from Store, so this process receives no Access
//! credential, OAuth request, response, code, client secret, or token. The neutral transport (`egress-transport`,
//! ADR-0104) resolves, records, connects, admits the TLS `ClientHello`, and splices; this profile owns its exact
//! request, audit record, and resource envelope.

use std::fmt;
use std::net::IpAddr;
use std::sync::Arc;
use std::time::Duration;

use egress_transport::{
    AuditError, AuditWriter, Decision, Envelope, Event, Fields, Json, Limits, Profile, Server,
    Target, Transport, refuse,
};

/// The port Store dials.
pub const PORT: u16 = 8889;
/// The audit stream.
pub const AUDIT_PATH: &str = "/var/log/store-egress/audit.jsonl";
/// The service name of every audit line.
pub const SERVICE: &str = "store-egress";
/// The one admitted destination host.
pub const ALLOWED_HOST: &str = "neuron.shimpz.com";
/// The one admitted destination port.
pub const ALLOWED_PORT: u16 = 443;
/// The only admitted request, byte for byte.
pub const EXACT_REQUEST: &[u8] =
    b"CONNECT neuron.shimpz.com:443 HTTP/1.1\r\nHost: neuron.shimpz.com:443\r\n\r\n";
/// The concurrency, per-source concurrency, and backlog.
pub const LIMITS: Limits = Limits {
    concurrency: 8,
    source_concurrency: 8,
    backlog: 8,
};
const SUBJECTS: [&str; 2] = ["neuron.shimpz.com:443", "rejected-target"];

/// The Store profile: its audit stream.
pub struct Store {
    audit: AuditWriter,
}

impl Store {
    /// A profile recording to `audit`.
    #[must_use]
    pub fn new(audit: AuditWriter) -> Self {
        Self { audit }
    }
}

impl Profile for Store {
    fn envelope(&self) -> Envelope {
        Envelope {
            connect_timeout: Duration::from_secs(10),
            idle_timeout: Duration::from_secs(30),
            request_limit: 1024,
            challenge: "",
        }
    }

    /// Network-gated: admit only the one exact Neuron request.
    fn admit(&self, request: &[u8], _client: IpAddr) -> Result<Target, Decision> {
        if request != EXACT_REQUEST {
            return Err(refuse(
                400,
                "request-rejected",
                "rejected-target",
                Fields::new(),
            ));
        }
        Ok(Target::new(ALLOWED_HOST, ALLOWED_PORT))
    }

    /// Persist one network-gated decision without request or credential content.
    fn record(&self, decision: &Decision) -> Result<(), AuditError> {
        self.audit.write(event(decision)?)
    }
}

/// The audit event of a decision, or an error for a subject this profile never records.
///
/// # Errors
///
/// The subject is not one this profile records.
pub fn event(decision: &Decision) -> Result<Event, AuditError> {
    if !SUBJECTS.contains(&decision.subject.as_str()) {
        return Err(AuditError("invalid Store egress audit event"));
    }
    Ok([
        ("principal_class", Json::from("machine")),
        ("principal_id", Json::from("store")),
        ("operation", Json::from("connect")),
        ("subject", Json::Str(decision.subject.clone())),
        ("result", Json::from(decision.result.as_str())),
        ("code", Json::Int(i64::from(decision.code))),
        ("reason", Json::Str(decision.reason.clone())),
    ]
    .into_iter()
    .map(|(key, value)| (key.to_owned(), value))
    .collect())
}

/// Why the profile refuses to start.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Startup {
    /// The audit directory's custody is unsafe or unavailable.
    Custody,
    /// The listener could not be bound.
    Listen,
}

impl fmt::Display for Startup {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::Custody => "audit custody is unavailable; refusing to start",
            Self::Listen => "the listener is unavailable; refusing to start",
        })
    }
}

/// The audit stream, the port, and the system interfaces.
pub struct Setup {
    /// The audit stream.
    pub audit: AuditWriter,
    /// The listening port.
    pub port: u16,
    /// The system interfaces.
    pub transport: Transport,
}

impl Setup {
    /// The image's paths, port, and system interfaces.
    #[must_use]
    pub fn production() -> Self {
        Self {
            audit: AuditWriter::new(AUDIT_PATH, SERVICE),
            port: PORT,
            transport: Transport::system(),
        }
    }
}

/// Check audit custody, then bind; nothing listens unless both hold.
///
/// # Errors
///
/// The first startup step that fails.
pub fn start(setup: Setup) -> Result<Server, Startup> {
    setup.audit.ensure_custody().map_err(|_| Startup::Custody)?;
    let profile = Arc::new(Store::new(setup.audit));
    Server::bind(setup.port, LIMITS, profile, Arc::new(setup.transport))
        .map_err(|_| Startup::Listen)
}

/// Start and serve forever; on a startup failure, say why and return 1.
pub fn run(setup: Setup) -> u8 {
    match start(setup) {
        Ok(server) => server.serve(),
        Err(startup) => {
            eprintln!("store-egress: {startup}");
            1
        }
    }
}

/// The image's entry: [`run`] with the production setup.
#[must_use]
pub fn main() -> u8 {
    run(Setup::production())
}

#[cfg(test)]
mod tests;
