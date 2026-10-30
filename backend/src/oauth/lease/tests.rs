use std::{path::Path, sync::Arc, time::Duration};

use super::{Fields, LEASE_TTL_SECONDS, LeaseSigner, digest};
use crate::{
    clock::ManualClock,
    oauth::{BrokerError, secret::tests::installed},
};

const ACCESS: &str = "access-token-0001";
const REFRESH: &str = "refresh-token-001";
const SCOPES: &str = "dns.read zone.read";
/// What the Python Store issued for these tokens and scopes at wall second 1,800,000,000.9 with the current key
/// 32 bytes of `n` and the previous 32 bytes of `q`.
const PYTHON_ISSUED: &str = concat!(
    "l3.6vqhNsWAqdA.1831622400.DlljrBP4Pmya82EKsPjc8zA-jkMs27TqjcNmfrPdbys.",
    "4WRbABMU62zbrHeGwL59YG2l-oQ9OowBElT4fZP1onQ.0rICXcrofJSCJFwxqWO9yLqWKNQEjCG9sLWXCdQ5b3w.",
    "KLavdCRbeb2PH5i9Tb5TwxY81mxJsrYDuIpPWoIh5V8"
);

fn signer(directory: &Path, current: &[u8], previous: &[u8]) -> (Arc<ManualClock>, LeaseSigner) {
    let clock = Arc::new(ManualClock::at(1_800_000_000));
    let paths = [
        installed(directory, "lease-key", current),
        installed(directory, "lease-key-previous", previous),
    ];
    (clock.clone(), LeaseSigner::new(paths, clock))
}

#[test]
fn a_lease_is_byte_identical_to_the_python_stores_and_verifies_under_either_key() {
    let directory = tempfile::tempdir().unwrap();
    let (_clock, current) = signer(directory.path(), &[b'n'; 32], &[b'q'; 32]);
    let lease = current.issue(ACCESS, REFRESH, SCOPES).unwrap();
    assert_eq!(lease, PYTHON_ISSUED);
    for token in [ACCESS, REFRESH] {
        assert_eq!(current.verify(&lease, token, Some(SCOPES)), Ok(()));
        assert_eq!(current.verify(&lease, token, None), Ok(()));
    }
    let rotated = tempfile::tempdir().unwrap();
    let (_clock, next) = signer(rotated.path(), &[b'r'; 32], &[b'n'; 32]);
    assert_eq!(next.verify(&lease, ACCESS, Some(SCOPES)), Ok(()));
    let retired = tempfile::tempdir().unwrap();
    let (_clock, after) = signer(retired.path(), &[b'r'; 32], &[b'q'; 32]);
    assert_eq!(after.verify(&lease, ACCESS, None), Err(BrokerError));
}

#[test]
fn a_lease_verifies_until_its_expiry_second() {
    let directory = tempfile::tempdir().unwrap();
    let (clock, signer) = signer(directory.path(), &[b'n'; 32], &[b'q'; 32]);
    let lease = signer.issue(ACCESS, REFRESH, SCOPES).unwrap();
    let ttl = u64::try_from(LEASE_TTL_SECONDS).unwrap();
    clock.step(Duration::from_secs(ttl - 1));
    assert_eq!(signer.verify(&lease, ACCESS, None), Ok(()));
    clock.step(Duration::from_secs(1));
    assert_eq!(signer.verify(&lease, ACCESS, None), Err(BrokerError));
}

#[test]
fn a_lease_naming_other_tokens_or_scopes_or_forged_is_refused() {
    let directory = tempfile::tempdir().unwrap();
    let (_clock, signer) = signer(directory.path(), &[b'n'; 32], &[b'q'; 32]);
    let lease = signer.issue(ACCESS, REFRESH, SCOPES).unwrap();
    assert_eq!(
        signer.verify(&lease, "another-token-001", None),
        Err(BrokerError)
    );
    assert_eq!(
        signer.verify(&lease, ACCESS, Some("dns.read")),
        Err(BrokerError)
    );
    let forged = format!("{}A", &lease[..lease.len() - 1]);
    let forged = if forged == lease {
        format!("{}B", &lease[..lease.len() - 1])
    } else {
        forged
    };
    assert_eq!(signer.verify(&forged, ACCESS, None), Err(BrokerError));
    let unknown = lease.replacen("6vqhNsWAqdA", "AAAAAAAAAAA", 1);
    assert_eq!(signer.verify(&unknown, ACCESS, None), Err(BrokerError));
}

#[test]
fn a_ring_needs_two_distinct_full_length_keys() {
    let refused: [(&[u8], &[u8]); 4] = [
        (&[b'n'; 32], &[b'n'; 32]),
        (&[b'n'; 31], &[b'q'; 32]),
        (&[b'n'; 32], &[b'q'; 31]),
        (&[b'n'; 32], &[b'q'; 33]),
    ];
    for (current, previous) in refused {
        let directory = tempfile::tempdir().unwrap();
        let (_clock, signer) = signer(directory.path(), current, previous);
        assert_eq!(signer.issue(ACCESS, REFRESH, SCOPES), Err(BrokerError));
        assert_eq!(signer.verify(PYTHON_ISSUED, ACCESS, None), Err(BrokerError));
    }
    let clock = Arc::new(ManualClock::at(0));
    let directory = tempfile::tempdir().unwrap();
    let previous = installed(directory.path(), "lease-key-previous", &[b'q'; 32]);
    let current = installed(directory.path(), "lease-key", &[b'n'; 32]);
    let missing = directory.path().join("missing");
    for paths in [[missing.clone(), previous], [current, missing]] {
        let signer = LeaseSigner::new(paths, clock.clone());
        assert_eq!(signer.issue(ACCESS, REFRESH, SCOPES), Err(BrokerError));
    }
}

#[test]
fn only_the_exact_lease_grammar_parses() {
    assert!(Fields::parse(PYTHON_ISSUED).is_some());
    let digest43 = "D".repeat(43);
    let malformed = [
        PYTHON_ISSUED.replacen("l3.", "l2.", 1),
        PYTHON_ISSUED.replacen("6vqhNsWAqdA", "6vqhNsWAqd", 1),
        PYTHON_ISSUED.replacen("6vqhNsWAqdA", "6vqhNsWAqd+", 1),
        PYTHON_ISSUED.replacen("1831622400", "183162240", 1),
        PYTHON_ISSUED.replacen("1831622400", "18316224\u{661}0", 1),
        PYTHON_ISSUED.replacen(
            "DlljrBP4Pmya82EKsPjc8zA-jkMs27TqjcNmfrPdbys",
            &digest43[..42],
            1,
        ),
        PYTHON_ISSUED.replacen("4WRbABMU62zbrHeGwL59YG2l-oQ9OowBElT4fZP1onQ", "", 1),
        PYTHON_ISSUED.replacen("0rICXcrofJSCJFwxqWO9yLqWKNQEjCG9sLWXCdQ5b3w", "=", 1),
        PYTHON_ISSUED.replacen(
            "KLavdCRbeb2PH5i9Tb5TwxY81mxJsrYDuIpPWoIh5V8",
            &digest43[..42],
            1,
        ),
        format!("{PYTHON_ISSUED}."),
        format!("{PYTHON_ISSUED}\n"),
    ];
    for lease in malformed {
        assert!(Fields::parse(&lease).is_none(), "{lease}");
    }
}

#[test]
fn a_malformed_lease_is_refused_before_the_ring_is_read() {
    let clock = Arc::new(ManualClock::at(0));
    let missing = Path::new("/nonexistent/lease-key").to_path_buf();
    let signer = LeaseSigner::new([missing.clone(), missing], clock);
    assert_eq!(signer.verify("l3.", ACCESS, None), Err(BrokerError));
    assert_eq!(signer.verify(PYTHON_ISSUED, ACCESS, None), Err(BrokerError));
}

#[test]
fn digests_are_unpadded_base64url_sha256() {
    assert_eq!(digest(""), "47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU");
    let production = LeaseSigner::production(Arc::new(ManualClock::at(0)));
    assert_eq!(
        production.paths[0].to_str(),
        Some("/run/shimpz-store-oauth/lease-key")
    );
    assert_eq!(
        production.paths[1].to_str(),
        Some("/run/shimpz-store-oauth/lease-key-previous")
    );
}
