//! Broker leases: a bounded proof that tokens came from one successful broker claim, under a two-key ring.
//!
//! A lease is `l3.{kid}.{exp}.{access}.{refresh}.{scopes}.{signature}`: the signing key's id
//! (`b64u(HMAC(key, "shimpz-oauth-broker-lease-kid")[:8])`), the wall-clock second it expires (366 days after
//! issue), the base64url SHA-256 digests of the access token, the refresh token, and the space-joined scopes, and the
//! base64url HMAC-SHA256 of everything before the last dot. The ring is read from both key files on every
//! operation: two distinct 32-byte keys whose ids differ, or the operation fails closed. The current key signs;
//! either verifies.

use std::{path::PathBuf, sync::Arc};

use base64::{Engine as _, engine::general_purpose::URL_SAFE_NO_PAD};
use hmac::{Hmac, KeyInit, Mac};
use sha2::{Digest, Sha256};
use subtle::ConstantTimeEq;
use zeroize::Zeroizing;

use super::{
    BrokerError,
    secret::{LEASE_KEY_PATH, PREVIOUS_LEASE_KEY_PATH, read_secret},
};
use crate::clock::Clock;

/// How long a lease verifies after it is issued.
pub const LEASE_TTL_SECONDS: i64 = 366 * 24 * 60 * 60;
const LEASE_KEY_BYTES: usize = 32;
const KEY_ID_LABEL: &[u8] = b"shimpz-oauth-broker-lease-kid";
const KEY_ID_CHARS: usize = 11;
const EXPIRY_DIGITS: usize = 10;
const DIGEST_CHARS: usize = 43;

/// One key of the ring with its id.
struct RingKey {
    id: String,
    key: Zeroizing<Vec<u8>>,
}

/// Issues and verifies leases with the key ring in two files.
pub struct LeaseSigner {
    paths: [PathBuf; 2],
    clock: Arc<dyn Clock>,
}

impl LeaseSigner {
    /// The signer of the deployed Store.
    #[must_use]
    pub fn production(clock: Arc<dyn Clock>) -> Self {
        Self::new(
            [
                PathBuf::from(LEASE_KEY_PATH),
                PathBuf::from(PREVIOUS_LEASE_KEY_PATH),
            ],
            clock,
        )
    }

    /// A signer reading the current key from the first path and the previous key from the second.
    #[must_use]
    pub fn new(paths: [PathBuf; 2], clock: Arc<dyn Clock>) -> Self {
        Self { paths, clock }
    }

    /// The ring, current key first.
    fn ring(&self) -> Result<[RingKey; 2], BrokerError> {
        let [current, previous] = [&self.paths[0], &self.paths[1]].map(|path| {
            read_secret(path, LEASE_KEY_BYTES as u64).map(|key| RingKey {
                id: key_id(&key),
                key,
            })
        });
        let ring = [current?, previous?];
        let distinct = ring[0].id != ring[1].id;
        let full = ring.iter().all(|entry| entry.key.len() == LEASE_KEY_BYTES);
        if distinct && full {
            Ok(ring)
        } else {
            Err(BrokerError)
        }
    }

    /// A lease for these tokens and space-joined scopes, signed by the current key.
    ///
    /// # Errors
    ///
    /// The key ring is unavailable.
    pub fn issue(&self, access: &str, refresh: &str, scopes: &str) -> Result<String, BrokerError> {
        let [current, _previous] = self.ring()?;
        let expires = self.clock.wall_seconds() + LEASE_TTL_SECONDS;
        let payload = format!(
            "l3.{}.{expires}.{}.{}.{}",
            current.id,
            digest(access),
            digest(refresh),
            digest(scopes)
        );
        let signature = signature(&current.key, &payload);
        Ok(format!("{payload}.{signature}"))
    }

    /// Require `lease` to be an unexpired lease of a ring key that names `token` as its access or refresh token and,
    /// when given, these space-joined scopes.
    ///
    /// # Errors
    ///
    /// The lease is malformed, unknown, expired, forged, or names other tokens or scopes, or the ring is unavailable.
    pub fn verify(
        &self,
        lease: &str,
        token: &str,
        scopes: Option<&str>,
    ) -> Result<(), BrokerError> {
        let fields = Fields::parse(lease).ok_or(BrokerError)?;
        let ring = self.ring()?;
        let key = ring
            .iter()
            .find(|entry| entry.id == fields.key_id)
            .ok_or(BrokerError)?;
        let payload = &lease[..lease.len() - DIGEST_CHARS - 1];
        let expected = signature(&key.key, payload);
        let presented = digest(token);
        let unexpired = fields.expires > self.clock.wall_seconds();
        let signed = bool::from(expected.as_bytes().ct_eq(fields.signature.as_bytes()));
        let names_token = bool::from(
            presented.as_bytes().ct_eq(fields.access.as_bytes())
                | presented.as_bytes().ct_eq(fields.refresh.as_bytes()),
        );
        let names_scopes = scopes.is_none_or(|scopes| {
            bool::from(fields.scopes.as_bytes().ct_eq(digest(scopes).as_bytes()))
        });
        if unexpired && signed && names_token && names_scopes {
            Ok(())
        } else {
            Err(BrokerError)
        }
    }
}

/// A lease's fields, each of its exact shape.
struct Fields<'a> {
    key_id: &'a str,
    expires: i64,
    access: &'a str,
    refresh: &'a str,
    scopes: &'a str,
    signature: &'a str,
}

impl<'a> Fields<'a> {
    /// `l3\.([A-Za-z0-9_-]{11})\.([0-9]{10})(\.[A-Za-z0-9_-]{43}){4}` and nothing more.
    fn parse(lease: &'a str) -> Option<Self> {
        let mut parts = lease.strip_prefix("l3.")?.split('.');
        let mut next = |length: usize, admitted: fn(u8) -> bool| {
            parts
                .next()
                .filter(|part| part.len() == length && part.bytes().all(admitted))
        };
        let key_id = next(KEY_ID_CHARS, base64url_char)?;
        let expires = next(EXPIRY_DIGITS, |byte| byte.is_ascii_digit())?;
        let [access, refresh, scopes, signature] =
            [(); 4].map(|()| next(DIGEST_CHARS, base64url_char));
        let fields = Self {
            key_id,
            expires: expires
                .bytes()
                .fold(0, |value, digit| value * 10 + i64::from(digit - b'0')),
            access: access?,
            refresh: refresh?,
            scopes: scopes?,
            signature: signature?,
        };
        parts.next().is_none().then_some(fields)
    }
}

fn base64url_char(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-')
}

fn mac(key: &[u8], message: &[u8]) -> [u8; 32] {
    let mut mac = Hmac::<Sha256>::new_from_slice(key).expect("HMAC accepts a key of any length");
    mac.update(message);
    mac.finalize().into_bytes().into()
}

fn key_id(key: &[u8]) -> String {
    URL_SAFE_NO_PAD.encode(&mac(key, KEY_ID_LABEL)[..8])
}

fn signature(key: &[u8], payload: &str) -> String {
    URL_SAFE_NO_PAD.encode(mac(key, payload.as_bytes()))
}

/// The base64url SHA-256 digest of a token or of space-joined scopes.
#[must_use]
pub fn digest(text: &str) -> String {
    URL_SAFE_NO_PAD.encode(Sha256::digest(text.as_bytes()))
}

#[cfg(test)]
mod tests;
