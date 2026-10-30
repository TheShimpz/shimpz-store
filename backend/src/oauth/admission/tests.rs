use std::{
    sync::{
        Arc,
        atomic::{AtomicUsize, Ordering},
    },
    time::Duration,
};

use http::StatusCode;
use tokio::sync::Notify;

use super::{Capacity, Operation, capacity_reached};
use crate::response::Reply;

/// An operation that counts itself running until `release` is notified.
fn held(release: &Arc<Notify>, running: &Arc<AtomicUsize>, peak: &Arc<AtomicUsize>) -> Operation {
    let (release, running, peak) = (Arc::clone(release), Arc::clone(running), Arc::clone(peak));
    Box::pin(async move {
        let now = running.fetch_add(1, Ordering::SeqCst) + 1;
        peak.fetch_max(now, Ordering::SeqCst);
        release.notified().await;
        running.fetch_sub(1, Ordering::SeqCst);
        Reply::detail(StatusCode::OK, "done", Vec::new())
    })
}

async fn settle() {
    for _ in 0..50 {
        tokio::task::yield_now().await;
    }
}

#[tokio::test]
async fn sixteen_operations_are_admitted_eight_run_and_the_seventeenth_is_refused() {
    let capacity = Capacity::default();
    let (release, running, peak) = (
        Arc::new(Notify::new()),
        Arc::new(AtomicUsize::new(0)),
        Arc::new(AtomicUsize::new(0)),
    );
    let handles: Vec<_> = (0..16)
        .map(|_| {
            capacity
                .admit()
                .unwrap()
                .spawn(held(&release, &running, &peak))
        })
        .collect();
    assert!(capacity.admit().is_none());
    settle().await;
    assert_eq!(running.load(Ordering::SeqCst), 8);
    while handles.iter().any(|handle| !handle.is_finished()) {
        release.notify_waiters();
        settle().await;
    }
    for handle in handles {
        assert_eq!(handle.await.unwrap().status, StatusCode::OK);
    }
    assert_eq!(peak.load(Ordering::SeqCst), 8);
    assert!(capacity.admit().is_some());
}

#[tokio::test]
async fn a_dropped_wait_keeps_the_operation_and_its_permits_until_it_ends() {
    let capacity = Arc::new(Capacity::new());
    let (release, running, peak) = (
        Arc::new(Notify::new()),
        Arc::new(AtomicUsize::new(0)),
        Arc::new(AtomicUsize::new(0)),
    );
    for _ in 0..16 {
        drop(
            capacity
                .admit()
                .unwrap()
                .spawn(held(&release, &running, &peak)),
        );
    }
    settle().await;
    assert!(capacity.admit().is_none());
    let drained = tokio::spawn({
        let capacity = Arc::clone(&capacity);
        async move { capacity.drained().await }
    });
    settle().await;
    assert!(!drained.is_finished());
    while !drained.is_finished() {
        release.notify_waiters();
        settle().await;
    }
    assert_eq!(running.load(Ordering::SeqCst), 0);
    assert!(
        capacity.admit().is_none(),
        "a drained capacity admits nothing"
    );
}

#[tokio::test]
async fn an_idle_capacity_drains_at_once() {
    let capacity = Capacity::new();
    tokio::time::timeout(Duration::from_secs(1), capacity.drained())
        .await
        .unwrap();
}

#[test]
fn the_capacity_refusal_asks_for_a_retry_after_one_second() {
    let reply = capacity_reached("/api/oauth/cloudflare/claim");
    assert_eq!(reply.status, StatusCode::TOO_MANY_REQUESTS);
    assert_eq!(
        &reply.body[..],
        b"{\"detail\":\"Store upstream capacity reached\"}"
    );
    let headers: Vec<_> = reply
        .headers
        .iter()
        .map(|(name, value)| (name.as_str(), value.to_str().unwrap()))
        .collect();
    assert_eq!(
        headers,
        [
            ("retry-after", "1"),
            ("content-length", "44"),
            ("content-type", "application/json")
        ]
    );
}

#[tokio::test]
async fn an_operation_admitted_before_shutdown_and_spawned_after_its_abort_is_aborted_at_once() {
    let capacity = Capacity::new();
    let admitted = capacity.admit().unwrap();
    capacity.abort();
    let pending: Operation = Box::pin(std::future::pending());
    let task = admitted.spawn(pending);
    let ended = tokio::time::timeout(Duration::from_secs(1), task)
        .await
        .unwrap();
    assert!(ended.unwrap_err().is_cancelled());
    tokio::time::timeout(Duration::from_secs(1), capacity.drained())
        .await
        .unwrap();
}
