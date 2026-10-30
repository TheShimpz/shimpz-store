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
async fn a_burst_of_visitors_shares_one_read_and_the_next_minute_reuses_it() {
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
async fn a_failed_catalog_read_is_never_kept() {
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
async fn a_read_that_waits_past_its_deadline_for_a_load_slot_is_refused() {
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

#[tokio::test]
async fn reads_of_different_locales_never_exceed_what_developers_loads_at_once() {
    let fake = fake(|target| {
        let locale = target.rsplit('=').next().unwrap().to_owned();
        let document =
            CATALOG.replacen("\"locale\":\"pt\"", &format!("\"locale\":\"{locale}\""), 1);
        Script::Reply(ok("application/json", document.as_bytes()))
    })
    .await;
    let catalogs = catalogs(&fake, &Arc::new(ManualClock::at(0)), 5_000);
    let reads: Vec<_> = ["en", "pt", "es", "fr", "de"]
        .into_iter()
        .map(|locale| {
            let catalogs = Arc::clone(&catalogs);
            tokio::spawn(async move { catalogs.served(locale).await })
        })
        .collect();
    for read in reads {
        assert!(read.await.unwrap().is_some());
    }
    assert!(fake.peak.load(std::sync::atomic::Ordering::SeqCst) <= 2);
}

#[tokio::test]
async fn json_transport_refuses_what_strict_json_refuses() {
    let duplicate = CATALOG.replacen("{\"version\":1,", "{\"version\":1,\"version\":1,", 1);
    let fake = fake(move |_| Script::Reply(ok("application/json", duplicate.as_bytes()))).await;
    let catalogs = catalogs(&fake, &Arc::new(ManualClock::at(0)), 5_000);
    assert_eq!(catalogs.served("pt").await, None);
}
