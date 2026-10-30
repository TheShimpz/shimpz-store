//! The broker's operation capacity: eight operations run and eight more wait; the seventeenth concurrent operation
//! is refused at once.
//!
//! Each admitted operation runs in its own task, which owns its admission and its execution permit, so a client that
//! disconnects drops only its wait for the outcome, never the operation: a Neuron call and the broker's own commit or
//! cleanup finish, and the permits return only when the operation ends.

use std::{
    future::Future,
    pin::Pin,
    sync::{Arc, Mutex, PoisonError},
};

use http::{HeaderValue, StatusCode, header};
use tokio::{
    sync::{OwnedSemaphorePermit, Semaphore},
    task::{AbortHandle, JoinHandle},
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
    tasks: Tasks,
}

/// The owned operation tasks that may still run, and whether shutdown has aborted them: one lock makes registering a
/// task and aborting every task atomic, so a task registered after the abort is aborted at once.
type Tasks = Arc<Mutex<Registry>>;

#[derive(Debug, Default)]
struct Registry {
    handles: Vec<AbortHandle>,
    aborted: bool,
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
            tasks: Tasks::default(),
        }
    }

    /// Admit one operation, or `None` when sixteen are already admitted.
    #[must_use]
    pub fn admit(&self) -> Option<Admitted> {
        let admission = Arc::clone(&self.admission).try_acquire_owned().ok()?;
        Some(Admitted {
            admission,
            execution: Arc::clone(&self.execution),
            tasks: Arc::clone(&self.tasks),
        })
    }

    /// Wait until every admitted operation has ended, and admit no other.
    pub async fn drained(&self) {
        let every = u32::try_from(ADMITTED).unwrap_or(u32::MAX);
        let _all = self.admission.acquire_many(every).await;
        self.admission.close();
    }

    /// Abort every owned operation task, and every task registered from now on; each drops its operation, whose
    /// guards restore the broker's state, and then its permits.
    pub fn abort(&self) {
        let mut registry = self.tasks.lock().unwrap_or_else(PoisonError::into_inner);
        registry.aborted = true;
        for task in &registry.handles {
            task.abort();
        }
    }
}

/// One admitted operation, not yet running.
#[derive(Debug)]
pub struct Admitted {
    admission: OwnedSemaphorePermit,
    execution: Arc<Semaphore>,
    tasks: Tasks,
}

impl Admitted {
    /// Run `operation` in its own task once a running slot is free; the task owns both permits until it ends.
    #[must_use]
    pub fn spawn(self, operation: Operation) -> JoinHandle<Reply> {
        let (admission, execution, tasks) = (self.admission, self.execution, self.tasks);
        let task = tokio::spawn(async move {
            let _admission = admission;
            let _running = execution.acquire_owned().await;
            operation.await
        });
        let mut registry = tasks.lock().unwrap_or_else(PoisonError::into_inner);
        if registry.aborted {
            task.abort();
        } else {
            registry.handles.retain(|task| !task.is_finished());
            registry.handles.push(task.abort_handle());
        }
        task
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
