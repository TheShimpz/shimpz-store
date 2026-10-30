//! The broker's secret files: Store's own, readable only by it, exactly as platform provisioning installs them.
//!
//! A file is opened without following a link and without blocking, so a FIFO without a writer is opened at once and
//! refused by `fstat` instead of pinning an operation. Before any read it must be a regular file owned by the
//! effective user, with one link, mode exactly `0400`, and a size from 1 to the file's maximum; then it is read up to
//! one byte past the maximum and must hold exactly the size `fstat` reported. Nothing is read at startup.

use std::{fs::File, io::Read, path::Path};

use rustix::fs::{FileType, Mode, OFlags};
use zeroize::Zeroizing;

use super::BrokerError;

/// The Access service token's client id.
pub const ACCESS_CLIENT_ID_PATH: &str = "/run/shimpz-store-oauth/access-client-id";
/// The Access service token's client secret.
pub const ACCESS_CLIENT_SECRET_PATH: &str = "/run/shimpz-store-oauth/access-client-secret";
/// The current lease key, which signs every new lease.
pub const LEASE_KEY_PATH: &str = "/run/shimpz-store-oauth/lease-key";
/// The previous lease key, which only verifies leases it signed before the last rotation.
pub const PREVIOUS_LEASE_KEY_PATH: &str = "/run/shimpz-store-oauth/lease-key-previous";
const SECRET_MODE: u32 = 0o400;
const MAX_CLIENT_ID_BYTES: u64 = 256;
const MAX_CLIENT_SECRET_BYTES: u64 = 1024;
const MIN_CLIENT_SECRET_BYTES: usize = 32;

/// What the file contract checks of an open secret file, before any read.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Metadata {
    /// Whether it is a regular file.
    pub regular: bool,
    /// Its owner.
    pub uid: u32,
    /// Whether it has exactly one link.
    pub single_link: bool,
    /// Its permission bits.
    pub mode: u32,
    /// Its size in bytes.
    pub size: i64,
}

impl Metadata {
    /// Whether a file with this metadata may be read as a secret of at most `maximum` bytes by user `euid`.
    #[must_use]
    pub fn admitted(&self, euid: u32, maximum: u64) -> bool {
        self.regular
            && self.uid == euid
            && self.single_link
            && self.mode == SECRET_MODE
            && u64::try_from(self.size).is_ok_and(|size| (1..=maximum).contains(&size))
    }
}

/// The contents of the secret file at `path`, of at most `maximum` bytes.
///
/// # Errors
///
/// The file cannot be opened or read, or it fails its file contract.
pub fn read_secret(path: &Path, maximum: u64) -> Result<Zeroizing<Vec<u8>>, BrokerError> {
    let flags = OFlags::RDONLY | OFlags::NOFOLLOW | OFlags::NONBLOCK | OFlags::CLOEXEC;
    let descriptor = rustix::fs::open(path, flags, Mode::empty()).or(Err(BrokerError))?;
    let stat = rustix::fs::fstat(&descriptor).or(Err(BrokerError))?;
    let metadata = Metadata {
        regular: FileType::from_raw_mode(stat.st_mode) == FileType::RegularFile,
        uid: stat.st_uid,
        single_link: stat.st_nlink == 1,
        mode: stat.st_mode & 0o7777,
        size: stat.st_size,
    };
    if !metadata.admitted(rustix::process::geteuid().as_raw(), maximum) {
        return Err(BrokerError);
    }
    exact(&mut File::from(descriptor), metadata.size, maximum)
}

/// Read at most one byte past `maximum` and require exactly `size` bytes.
fn exact(file: &mut dyn Read, size: i64, maximum: u64) -> Result<Zeroizing<Vec<u8>>, BrokerError> {
    let mut contents = Zeroizing::new(Vec::new());
    file.take(maximum + 1)
        .read_to_end(&mut contents)
        .or(Err(BrokerError))?;
    if i64::try_from(contents.len()) == Ok(size) {
        Ok(contents)
    } else {
        Err(BrokerError)
    }
}

/// The Access service token Store presents to Neuron.
pub struct AccessCredential {
    /// `CF-Access-Client-Id`.
    pub client_id: String,
    /// `CF-Access-Client-Secret`.
    pub client_secret: Zeroizing<String>,
}

/// Read the Access service token from its two files: a client id `[A-Za-z0-9_-]{16,128}.access` and a secret of 32 to
/// 1,024 printable ASCII characters.
///
/// # Errors
///
/// Either file fails its contract, or either value its shape.
pub fn access_credential(
    id_path: &Path,
    secret_path: &Path,
) -> Result<AccessCredential, BrokerError> {
    let id = read_secret(id_path, MAX_CLIENT_ID_BYTES)?;
    let secret = read_secret(secret_path, MAX_CLIENT_SECRET_BYTES)?;
    let client_id = std::str::from_utf8(&id)
        .ok()
        .filter(|id| client_id_shaped(id))
        .ok_or(BrokerError)?
        .to_owned();
    if secret.len() < MIN_CLIENT_SECRET_BYTES || !printable(&secret) {
        return Err(BrokerError);
    }
    let client_secret = Zeroizing::new(secret.iter().map(|byte| char::from(*byte)).collect());
    Ok(AccessCredential {
        client_id,
        client_secret,
    })
}

/// Whether every byte is printable ASCII without a space.
#[must_use]
pub fn printable(bytes: &[u8]) -> bool {
    bytes.iter().all(|byte| (b'!'..=b'~').contains(byte))
}

fn client_id_shaped(id: &str) -> bool {
    id.strip_suffix(".access").is_some_and(|name| {
        (16..=128).contains(&name.len())
            && name
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-'))
    })
}

#[cfg(test)]
pub(crate) mod tests;
