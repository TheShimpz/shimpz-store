use std::{
    fs,
    io::Cursor,
    os::unix::fs::{PermissionsExt, symlink},
    path::{Path, PathBuf},
    time::{Duration, Instant},
};

use super::{Metadata, access_credential, exact, printable, read_secret};
use crate::oauth::BrokerError;

/// A secret file holding `contents`, installed as provisioning installs it.
pub fn installed(directory: &Path, name: &str, contents: &[u8]) -> PathBuf {
    let path = directory.join(name);
    fs::write(&path, contents).unwrap();
    fs::set_permissions(&path, fs::Permissions::from_mode(0o400)).unwrap();
    path
}

#[test]
fn an_installed_secret_is_read_whole() {
    let directory = tempfile::tempdir().unwrap();
    let path = installed(directory.path(), "secret", b"value");
    assert_eq!(read_secret(&path, 5).unwrap().as_slice(), b"value");
    assert_eq!(read_secret(&path, 4).err(), Some(BrokerError));
}

#[test]
fn a_secret_that_is_missing_linked_or_loosely_installed_is_refused() {
    let directory = tempfile::tempdir().unwrap();
    let path = installed(directory.path(), "secret", b"value");
    let link = directory.path().join("link");
    symlink(&path, &link).unwrap();
    let hard = directory.path().join("hard");
    fs::hard_link(installed(directory.path(), "other", b"value"), &hard).unwrap();
    let loose = directory.path().join("loose");
    fs::write(&loose, b"value").unwrap();
    let empty = installed(directory.path(), "empty", b"");
    for refused in [
        &directory.path().join("missing"),
        &link,
        &hard,
        &loose,
        &empty,
        directory.path(),
    ] {
        assert_eq!(
            read_secret(refused, 64).err(),
            Some(BrokerError),
            "{refused:?}"
        );
    }
}

#[test]
fn a_fifo_without_a_writer_is_refused_at_once() {
    let directory = tempfile::tempdir().unwrap();
    let fifo = directory.path().join("fifo");
    rustix::fs::mknodat(
        rustix::fs::CWD,
        &fifo,
        rustix::fs::FileType::Fifo,
        rustix::fs::Mode::from_raw_mode(0o400),
        0,
    )
    .unwrap();
    let started = Instant::now();
    assert_eq!(read_secret(&fifo, 64).err(), Some(BrokerError));
    assert!(started.elapsed() < Duration::from_secs(2));
}

#[test]
fn the_file_contract_admits_only_a_single_linked_owner_read_only_regular_file_in_size() {
    let good = Metadata {
        regular: true,
        uid: 1000,
        single_link: true,
        mode: 0o400,
        size: 32,
    };
    assert!(good.admitted(1000, 32));
    assert!(Metadata { size: 1, ..good }.admitted(1000, 32));
    let refused = [
        (
            Metadata {
                regular: false,
                ..good
            },
            32,
        ),
        (Metadata { uid: 0, ..good }, 32),
        (
            Metadata {
                single_link: false,
                ..good
            },
            32,
        ),
        (
            Metadata {
                mode: 0o600,
                ..good
            },
            32,
        ),
        (
            Metadata {
                mode: 0o4400,
                ..good
            },
            32,
        ),
        (Metadata { size: 0, ..good }, 32),
        (Metadata { size: -1, ..good }, 32),
        (good, 31),
    ];
    for (metadata, maximum) in refused {
        assert!(!metadata.admitted(1000, maximum), "{metadata:?} {maximum}");
    }
}

struct Broken;
impl std::io::Read for Broken {
    fn read(&mut self, _: &mut [u8]) -> std::io::Result<usize> {
        Err(std::io::Error::other("broken"))
    }
}

#[test]
fn a_secret_must_hold_exactly_the_size_its_metadata_reported() {
    assert_eq!(
        exact(&mut Cursor::new(b"value"), 5, 8).unwrap().as_slice(),
        b"value"
    );
    assert_eq!(
        exact(&mut Cursor::new(b"val"), 5, 8).err(),
        Some(BrokerError)
    );
    assert_eq!(
        exact(&mut Cursor::new(b"value-longer"), 5, 8).err(),
        Some(BrokerError)
    );
    assert_eq!(exact(&mut Broken, 5, 8).err(), Some(BrokerError));
}

#[test]
fn the_access_credential_needs_an_exact_client_id_and_a_printable_secret() {
    let directory = tempfile::tempdir().unwrap();
    let id = format!("{}.access", "i".repeat(16));
    let secret = "s".repeat(32);
    let id_path = installed(directory.path(), "id", id.as_bytes());
    let secret_path = installed(directory.path(), "secret", secret.as_bytes());
    let credential = access_credential(&id_path, &secret_path).unwrap();
    assert_eq!(credential.client_id, id);
    assert_eq!(credential.client_secret.as_str(), secret);
    let refused_ids = [
        format!("{}.access", "i".repeat(15)),
        format!("{}.access", "i".repeat(129)),
        format!("{}.acces", "i".repeat(16)),
        format!("{}.access", "i.".repeat(8)),
        format!("{}\u{e9}.access", "i".repeat(16)),
        String::from("\u{ff}"),
    ];
    for (index, refused) in refused_ids.iter().enumerate() {
        let path = installed(directory.path(), &format!("id-{index}"), refused.as_bytes());
        assert!(access_credential(&path, &secret_path).is_err(), "{refused}");
    }
    let refused_secrets: [&[u8]; 3] = [
        &[b's'; 31],
        b"sssssssssssssssssssssssssssssss s",
        b"sssssssssssssssssssssssssssssss\xff",
    ];
    for (index, refused) in refused_secrets.iter().enumerate() {
        let path = installed(directory.path(), &format!("secret-{index}"), refused);
        assert!(access_credential(&id_path, &path).is_err(), "{refused:?}");
    }
    let missing = directory.path().join("missing");
    assert!(access_credential(&missing, &secret_path).is_err());
    assert!(access_credential(&id_path, &missing).is_err());
}

#[test]
fn printable_means_ascii_from_exclamation_mark_to_tilde() {
    assert!(printable(b"!~azAZ09"));
    assert!(!printable(b" "));
    assert!(!printable(b"\x7f"));
    assert!(!printable(b"\x80"));
}
