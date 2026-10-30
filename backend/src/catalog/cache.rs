//! The public catalog cache: one locale's projected catalog is kept for 60 s, and only one read of a locale runs at
//! a time: every visitor arriving meanwhile shares it, and a leaving visitor never cancels it. A read first takes one
//! of Developers' two catalog load slots, waiting at most 5 s; a failed read is never kept.

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
use strict_json::Value;
use tokio::sync::Semaphore;

use super::{
    project::project,
    upstream::{Developers, MAX_JSON_BYTES, log_failure},
};
use crate::{
    clock::Clock,
    log::{Level, event},
};

/// How long a read catalog is served.
pub const LIFETIME: Duration = Duration::from_secs(60);
/// How many catalogs Developers loads at once.
pub const LOAD_SLOTS: usize = 2;

/// A served catalog: when it was read, on the monotonic clock, and its bytes.
pub type Served = (Duration, Bytes);
type Read = Shared<BoxFuture<'static, Option<Served>>>;

/// The catalogs of every locale, read from Developers on demand.
pub struct Catalogs {
    developers: Developers,
    clock: Arc<dyn Clock>,
    slots: Semaphore,
    slot_wait: Duration,
    state: Mutex<State>,
}

#[derive(Default)]
struct State {
    kept: HashMap<&'static str, Served>,
    reading: HashMap<&'static str, Read>,
}

impl Catalogs {
    /// Catalogs read from `developers`, timed by `clock`, waiting at most `slot_wait` for a load slot.
    #[must_use]
    pub fn new(developers: Developers, clock: Arc<dyn Clock>, slot_wait: Duration) -> Self {
        Self {
            developers,
            clock,
            slots: Semaphore::new(LOAD_SLOTS),
            slot_wait,
            state: Mutex::default(),
        }
    }

    /// The time on the clock the catalogs are kept by.
    #[must_use]
    pub fn now(&self) -> Duration {
        self.clock.monotonic()
    }

    /// One locale's catalog and when it was read, kept or read now; `None` when it is unavailable.
    pub async fn served(self: &Arc<Self>, locale: &'static str) -> Option<Served> {
        let read = {
            let mut state = self.state.lock().unwrap_or_else(PoisonError::into_inner);
            if let Some(kept) = state.kept.get(locale)
                && self.now().saturating_sub(kept.0) < LIFETIME
            {
                return Some(kept.clone());
            }
            state
                .reading
                .entry(locale)
                .or_insert_with(|| self.spawn_read(locale))
                .clone()
        };
        read.await
    }

    /// Start one read of `locale` that runs to its end whoever still waits for it.
    fn spawn_read(self: &Arc<Self>, locale: &'static str) -> Read {
        let this = Arc::clone(self);
        let task = tokio::spawn(async move {
            let read = this.read(locale).await;
            let mut state = this.state.lock().unwrap_or_else(PoisonError::into_inner);
            state.reading.remove(locale);
            if let Some(served) = &read {
                state.kept.insert(locale, served.clone());
            }
            read
        });
        async move { task.await.ok().flatten() }.boxed().shared()
    }

    async fn read(&self, locale: &'static str) -> Option<Served> {
        let _slot = tokio::time::timeout(self.slot_wait, self.slots.acquire())
            .await
            .ok()
            .and_then(Result::ok)?;
        let path = format!("/api/v1/assistants?locale={locale}");
        let fetched = match self.developers.get(&path, None, MAX_JSON_BYTES).await {
            Ok(fetched) => fetched,
            Err(failure) => {
                log_failure("proxy_unreachable", &path, failure);
                return None;
            }
        };
        let body = fetched
            .body
            .filter(|_| fetched.status == http::StatusCode::OK)?;
        let value = if body.is_empty() {
            Value::Object(Vec::new())
        } else if let Ok(value) = strict_json::parse(&body) {
            value
        } else {
            event(
                Level::Warning,
                "proxy_unreachable",
                &[("path", &path), ("error", "invalid_json")],
            );
            return None;
        };
        let projected = project(&value, locale)?;
        Some((self.now(), Bytes::from(projected)))
    }
}

#[cfg(test)]
mod tests;
