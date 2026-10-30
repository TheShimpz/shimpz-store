//! Assistant icons: read from Developers only when both digests are well formed, kept by their icon digest within
//! 256 icons and 8 MiB (least recently used first out), at most 64 distinct reads pending, two loading at once after
//! a wait of at most 5 s for a slot; only bytes whose SHA-256 is the icon digest are served.

use std::{
    collections::HashMap,
    sync::{Arc, Mutex, PoisonError},
    time::Duration,
};

use bytes::Bytes;
use futures_util::{
    FutureExt,
    future::{BoxFuture, Shared},
};
use sha2::{Digest, Sha256};
use tokio::sync::Semaphore;

use super::upstream::{Developers, Fetched, MAX_ASSET_BYTES, log_failure};

/// The most icons kept.
pub const MAX_KEPT_ICONS: usize = 256;
/// The most icon bytes kept.
pub const MAX_KEPT_BYTES: usize = 8 * 1024 * 1024;
/// The most distinct icons read or waiting for a load slot at once.
pub const MAX_PENDING_READS: usize = 64;
/// How many icons Developers loads at once.
pub const LOAD_SLOTS: usize = 2;
/// The most digits an admitted `Content-Length` has: that of [`MAX_ASSET_BYTES`].
const MAX_LENGTH_DIGITS: usize = 7;

type Key = (String, String);
type Read = Shared<BoxFuture<'static, Option<Bytes>>>;

/// The icons of every publication, read from Developers on demand.
pub struct Icons {
    developers: Developers,
    slots: Semaphore,
    slot_wait: Duration,
    state: Mutex<State>,
}

#[derive(Default)]
struct State {
    /// Kept icons, least recently used first.
    kept: Vec<(Key, Bytes)>,
    reading: HashMap<Key, Read>,
}

impl State {
    fn keep(&mut self, key: Key, icon: Bytes) {
        self.kept.retain(|(kept, _)| *kept != key);
        self.kept.push((key, icon));
        while self.kept.len() > MAX_KEPT_ICONS
            || self.kept.iter().map(|(_, icon)| icon.len()).sum::<usize>() > MAX_KEPT_BYTES
        {
            self.kept.remove(0);
        }
    }
}

impl Icons {
    /// Icons read from `developers`, waiting at most `slot_wait` for a load slot.
    #[must_use]
    pub fn new(developers: Developers, slot_wait: Duration) -> Self {
        Self {
            developers,
            slots: Semaphore::new(LOAD_SLOTS),
            slot_wait,
            state: Mutex::default(),
        }
    }

    /// The verified icon of a publication, kept or read now; `None` when it is unavailable.
    pub async fn icon(self: &Arc<Self>, source: &str, icon: &str) -> Option<Bytes> {
        let key = (source.to_owned(), icon.to_owned());
        let read = {
            let mut state = self.state.lock().unwrap_or_else(PoisonError::into_inner);
            if let Some(position) = state.kept.iter().position(|(kept, _)| *kept == key) {
                let entry = state.kept.remove(position);
                state.kept.push(entry.clone());
                return Some(entry.1);
            }
            match state.reading.get(&key) {
                Some(read) => read.clone(),
                None if state.reading.len() >= MAX_PENDING_READS => return None,
                None => {
                    let read = self.spawn_read(key.clone());
                    state.reading.insert(key, read.clone());
                    read
                }
            }
        };
        read.await
    }

    fn spawn_read(self: &Arc<Self>, key: Key) -> Read {
        let this = Arc::clone(self);
        let task = tokio::spawn(async move {
            let read = this.read(&key).await;
            let mut state = this.state.lock().unwrap_or_else(PoisonError::into_inner);
            state.reading.remove(&key);
            if let Some(icon) = &read {
                state.keep(key, icon.clone());
            }
            read
        });
        async move { task.await.ok().flatten() }.boxed().shared()
    }

    async fn read(&self, (source, icon): &Key) -> Option<Bytes> {
        let _slot = tokio::time::timeout(self.slot_wait, self.slots.acquire())
            .await
            .ok()
            .and_then(Result::ok)?;
        let path = format!("/api/v1/assistant-publications/sha256:{source}/icon.png");
        let fetched = match self
            .developers
            .get(&path, Some("image/png"), MAX_ASSET_BYTES)
            .await
        {
            Ok(fetched) => fetched,
            Err(failure) => {
                log_failure("asset_proxy_unreachable", &path, failure);
                return None;
            }
        };
        let contents = admitted(fetched)?;
        (hex(&Sha256::digest(&contents)) == *icon).then_some(contents)
    }
}

/// The body of a `200 image/png` reply whose `Content-Length` is 1 to 1 MiB in ASCII digits and equals its length.
fn admitted(fetched: Fetched) -> Option<Bytes> {
    if fetched.status != http::StatusCode::OK {
        return None;
    }
    let content_type = fetched.content_type.unwrap_or_default();
    let media_type =
        team_protocol::python::text::strip(content_type.split(';').next().unwrap_or_default());
    let length = fetched.content_length.filter(|length| {
        length.len() <= MAX_LENGTH_DIGITS
            && !length.is_empty()
            && length.bytes().all(|byte| byte.is_ascii_digit())
    })?;
    let expected: usize = length.parse().ok()?;
    let body = fetched.body?;
    let fits = (1..=MAX_ASSET_BYTES).contains(&expected) && body.len() == expected;
    (media_type.to_lowercase() == "image/png" && fits).then_some(body)
}

/// The lowercase hexadecimal form of a digest.
pub(super) fn hex(digest: &[u8]) -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    digest
        .iter()
        .flat_map(|byte| {
            [
                DIGITS[usize::from(byte >> 4)],
                DIGITS[usize::from(byte & 15)],
            ]
        })
        .map(char::from)
        .collect()
}

#[cfg(test)]
mod tests;
