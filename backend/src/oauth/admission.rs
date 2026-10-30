//! The broker's operation capacity: eight operations run and eight more wait; the seventeenth concurrent operation
//! is refused at once.
//!
//! Each admitted operation runs in its own task, which owns its admission and its execution permit, so a client that
//! disconnects drops only its wait for the outcome, never the operation: a Neuron call and the broker's own commit or
//! cleanup finish, and the permits return only when the operation ends.

use std::{future::Future, pin::Pin, sync::Arc};

use http::{HeaderValue, StatusCode, header};
use tokio::{
    sync::{OwnedSemaphorePermit, Semaphore},
    task::JoinHandle,
};

use crate::{log, response::Reply};

/// How many broker operations run at once.
pub const RUNNING: usize = 8;
/// How many admitted operations may wait for a running slot.
pub const QUEUED: usize = 8;
const ADMITTED: usize = RUNNING + QUEUED;

/// One broker operation, producing its reply.
pub type Operation = Pin<Box<dyn Future<Output = Reply> + Send>>;

/// The broker's admission and execution bounds.
#[derive(Debug)]
pub struct Capacity {
    admission: Arc<Semaphore>,
    execution: Arc<Semaphore>,
}

impl Default for Capacity {
    fn default() -> Self {
        Self::new()
    }
}

impl Capacity {
    /// Room for eight running and eight waiting operations.
    #[must_use]
    pub fn new() -> Self {
        Self {
            admission: Arc::new(Semaphore::new(ADMITTED)),
            execution: Arc::new(Semaphore::new(RUNNING)),
        }
    }

    /// Admit one operation, or `None` when sixteen are already admitted.
    #[must_use]
    pub fn admit(&self) -> Option<Admitted> {
        let admission = Arc::clone(&self.admission).try_acquire_owned().ok()?;
        Some(Admitted {
            admission,
            execution: Arc::clone(&self.execution),
        })
    }

    /// Wait until every admitted operation has ended, and admit no other.
    pub async fn drained(&self) {
        let every = u32::try_from(ADMITTED).unwrap_or(u32::MAX);
        let _all = self.admission.acquire_many(every).await;
        self.admission.close();
    }
}

/// One admitted operation, not yet running.
#[derive(Debug)]
pub struct Admitted {
    admission: OwnedSemaphorePermit,
    execution: Arc<Semaphore>,
}

impl Admitted {
    /// Run `operation` in its own task once a running slot is free; the task owns both permits until it ends.
    #[must_use]
    pub fn spawn(self, operation: Operation) -> JoinHandle<Reply> {
        tokio::spawn(async move {
            let _admission = self.admission;
            let _running = self.execution.acquire_owned().await;
            operation.await
        })
    }
}

/// The refusal of an operation past the capacity, logged with the request's decoded path.
#[must_use]
pub fn capacity_reached(path: &str) -> Reply {
    log::event(
        log::Level::Warning,
        "store_capacity_rejected",
        &[("path", path)],
    );
    Reply::detail(
        StatusCode::TOO_MANY_REQUESTS,
        "Store upstream capacity reached",
        vec![(header::RETRY_AFTER, HeaderValue::from_static("1"))],
    )
}

#[cfg(test)]
mod tests;
