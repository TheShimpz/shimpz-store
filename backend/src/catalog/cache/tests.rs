use std::{sync::Arc, time::Duration};

use tokio::sync::Notify;

use super::{Catalogs, LIFETIME};
use crate::{
    catalog::testing::{Script, fake, ok},
    clock::ManualClock,
};

const CATALOG: &str = include_str!("../project/catalog.json");
const PATH: &str = "/api/v1/assistants?locale=pt";

fn catalogs(
    fake: &crate::catalog::testing::Fake,
    clock: &Arc<ManualClock>,
    slot_wait: u64,
) -> Arc<Catalogs> {
    let clock: Arc<dyn crate::clock::Clock> = clock.clone();
    Arc::new(Catalogs::new(
        fake.developers.clone(),
        clock,
        Duration::from_millis(slot_wait),
    ))
}

#[tokio::test]
async fn a_read_catalog_is_kept_for_its_lifetime_and_then_read_again() {
    let fake = fake(|_| Script::Reply(ok("application/json", CATALOG.as_bytes()))).await;
    let clock = Arc::new(ManualClock::at(0));
    let catalogs = catalogs(&fake, &clock, 5_000);
    let (read_at, body) = catalogs.served("pt").await.unwrap();
    assert_eq!(read_at, Duration::ZERO);
    assert_eq!(body, include_str!("../project/projected.json").as_bytes());
    clock.step(LIFETIME.saturating_sub(Duration::from_secs(1)));
    assert_eq!(catalogs.served("pt").await.unwrap().0, Duration::ZERO);
    assert_eq!(fake.calls(PATH), 1);
    clock.step(Duration::from_secs(1));
    assert_eq!(catalogs.served("pt").await.unwrap().0, LIFETIME);
    assert_eq!(fake.calls(PATH), 2);
}

#[tokio::test]
async fn refused_unreadable_or_failed_reads_are_never_kept() {
    let replies = [
        b"HTTP/1.1 503 Busy\r\nContent-Length: 2\r\n\r\n{}".to_vec(),
        ok("application/json", b""),
        ok("application/json", b"{"),
        ok(
            "application/json",
            b"{\"version\":1,\"locale\":\"en\",\"assistants\":[]}",
        ),
        ok("application/json", &vec![b' '; super::MAX_JSON_BYTES + 1]),
    ];
    for reply in replies {
        let fake = fake(move |_| Script::Reply(reply.clone())).await;
        let catalogs = catalogs(&fake, &Arc::new(ManualClock::at(0)), 5_000);
        assert_eq!(catalogs.served("pt").await, None);
        assert_eq!(catalogs.served("pt").await, None);
        assert_eq!(fake.calls(PATH), 2);
    }
}

#[tokio::test]
async fn an_unreachable_developers_answers_unavailable() {
    let fake = fake(|_| Script::Reply(Vec::new())).await;
    let mut developers = fake.developers.clone();
    developers.port = tokio::net::TcpListener::bind("127.0.0.1:0")
        .await
        .unwrap()
        .local_addr()
        .unwrap()
        .port();
    let clock: Arc<dyn crate::clock::Clock> = Arc::new(ManualClock::at(0));
    let catalogs = Arc::new(Catalogs::new(developers, clock, Duration::from_secs(5)));
    assert_eq!(catalogs.served("pt").await, None);
}

#[tokio::test]
async fn concurrent_visitors_share_one_read_that_a_leaving_visitor_never_cancels() {
    let release = Arc::new(Notify::new());
    let held = Arc::clone(&release);
    let fake = fake(move |_| {
        Script::Held(
            Arc::clone(&held),
            ok("application/json", CATALOG.as_bytes()),
        )
    })
    .await;
    let catalogs = catalogs(&fake, &Arc::new(ManualClock::at(0)), 5_000);
    let leaving = tokio::spawn({
        let catalogs = Arc::clone(&catalogs);
        async move { catalogs.served("pt").await }
    });
    fake.wait_active(1).await;
    leaving.abort();
    let waiters: Vec<_> = (0..5)
        .map(|_| {
            let catalogs = Arc::clone(&catalogs);
            tokio::spawn(async move { catalogs.served("pt").await })
        })
        .collect();
    tokio::time::sleep(Duration::from_millis(50)).await;
    release.notify_waiters();
    for waiter in waiters {
        assert!(waiter.await.unwrap().is_some());
    }
    assert_eq!(fake.calls(PATH), 1);
}

#[tokio::test]
async fn a_read_waiting_past_its_deadline_for_one_of_two_load_slots_is_refused() {
    let release = Arc::new(Notify::new());
    let held = Arc::clone(&release);
    let fake = fake(move |target| {
        let catalog = CATALOG.replace(
            "\"locale\":\"pt\"",
            &format!("\"locale\":\"{}\"", &target[target.len() - 2..]),
        );
        Script::Held(
            Arc::clone(&held),
            ok("application/json", catalog.as_bytes()),
        )
    })
    .await;
    let catalogs = catalogs(&fake, &Arc::new(ManualClock::at(0)), 100);
    let loads: Vec<_> = ["pt", "de"]
        .into_iter()
        .map(|locale| {
            let catalogs = Arc::clone(&catalogs);
            tokio::spawn(async move { catalogs.served(locale).await })
        })
        .collect();
    fake.wait_active(2).await;
    assert_eq!(catalogs.served("fr").await, None);
    assert_eq!(fake.peak.load(std::sync::atomic::Ordering::SeqCst), 2);
    release.notify_waiters();
    for load in loads {
        assert!(load.await.unwrap().is_some());
    }
}
