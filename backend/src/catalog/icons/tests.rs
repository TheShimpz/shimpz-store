use std::{sync::Arc, time::Duration};

use bytes::Bytes;
use sha2::{Digest, Sha256};
use tokio::sync::Notify;

use super::{Icons, MAX_KEPT_BYTES, MAX_KEPT_ICONS, MAX_PENDING_READS, State, admitted, hex};
use crate::catalog::{
    testing::{Script, fake, ok},
    upstream::{Fetched, MAX_ASSET_BYTES},
};

fn icon(seed: u8, size: usize) -> Vec<u8> {
    vec![seed; size]
}

fn digest(bytes: &[u8]) -> String {
    hex(&Sha256::digest(bytes))
}

fn source(seed: u8) -> String {
    format!("{seed:02x}").repeat(32)
}

#[tokio::test]
async fn a_verified_icon_is_read_once_and_then_kept() {
    let fake =
        fake(|target| Script::Reply(ok("image/png", &icon(target.as_bytes()[39], 32)))).await;
    let icons = Arc::new(Icons::new(fake.developers.clone(), Duration::from_secs(5)));
    let bytes = icon(b'1', 32);
    let path = format!(
        "/api/v1/assistant-publications/sha256:{}/icon.png",
        source(0x11)
    );
    assert_eq!(
        icons.icon(&source(0x11), &digest(&bytes)).await.as_deref(),
        Some(&bytes[..])
    );
    assert_eq!(
        icons.icon(&source(0x11), &digest(&bytes)).await.as_deref(),
        Some(&bytes[..])
    );
    assert_eq!(fake.calls(&path), 1);
    assert_eq!(icons.icon(&source(0x11), &"0".repeat(64)).await, None);
    assert_eq!(icons.icon(&source(0x11), &"0".repeat(64)).await, None);
    assert_eq!(fake.calls(&path), 3);
    let request = fake.calls.lock().unwrap().len();
    assert_eq!(request, 1);
}

#[tokio::test]
async fn asset_transport_closes_on_network_failure() {
    let mut developers = fake(|_| Script::Reply(Vec::new())).await.developers;
    developers.port = tokio::net::TcpListener::bind("127.0.0.1:0")
        .await
        .unwrap()
        .local_addr()
        .unwrap()
        .port();
    let icons = Arc::new(Icons::new(developers, Duration::from_secs(5)));
    assert_eq!(icons.icon(&source(1), &"0".repeat(64)).await, None);
    let release = Arc::new(Notify::new());
    let held = Arc::clone(&release);
    let fake = fake(move |_| Script::Held(Arc::clone(&held), ok("image/png", b"x"))).await;
    let icons = Arc::new(Icons::new(
        fake.developers.clone(),
        Duration::from_millis(100),
    ));
    let loads: Vec<_> = (1..=2)
        .map(|seed| {
            let icons = Arc::clone(&icons);
            tokio::spawn(async move { icons.icon(&source(seed), &digest(b"x")).await })
        })
        .collect();
    fake.wait_active(2).await;
    assert_eq!(icons.icon(&source(3), &digest(b"x")).await, None);
    release.notify_waiters();
    for load in loads {
        assert!(load.await.unwrap().is_some());
    }
}

#[tokio::test]
async fn icons_past_the_pending_bound_are_refused_and_never_queued() {
    let release = Arc::new(Notify::new());
    let held = Arc::clone(&release);
    let fake = fake(move |_| Script::Held(Arc::clone(&held), ok("image/png", b"x"))).await;
    let icons = Arc::new(Icons::new(fake.developers.clone(), Duration::from_secs(60)));
    let pending: Vec<_> = (0..MAX_PENDING_READS)
        .map(|index| {
            let icons = Arc::clone(&icons);
            let seed = u8::try_from(index % 2).unwrap();
            let source = format!("{index:064x}");
            let _ = seed;
            tokio::spawn(async move { icons.icon(&source, &digest(b"x")).await })
        })
        .collect();
    let shared = {
        let icons = Arc::clone(&icons);
        tokio::spawn(async move { icons.icon(&format!("{:064x}", 0), &digest(b"x")).await })
    };
    fake.wait_active(2).await;
    while icons.state.lock().unwrap().reading.len() < MAX_PENDING_READS {
        tokio::time::sleep(Duration::from_millis(5)).await;
    }
    assert_eq!(icons.icon(&"f".repeat(64), &digest(b"x")).await, None);
    release.notify_waiters();
    for read in pending {
        let mut read = read;
        loop {
            tokio::select! {
                result = &mut read => { assert!(result.unwrap().is_some()); break; }
                () = tokio::time::sleep(Duration::from_millis(20)) => release.notify_waiters(),
            }
        }
    }
    assert!(shared.await.unwrap().is_some());
}

#[test]
fn kept_icons_stay_within_their_count_and_byte_budgets() {
    let mut state = State::default();
    for index in 0..=MAX_KEPT_ICONS {
        state.keep((index.to_string(), String::new()), Bytes::from_static(b"x"));
    }
    assert_eq!(state.kept.len(), MAX_KEPT_ICONS);
    assert_eq!(state.kept[0].0.0, "1");
    state.keep(("1".into(), String::new()), Bytes::from_static(b"y"));
    assert_eq!(state.kept.last().unwrap().0.0, "1");
    let large = Bytes::from(vec![0; MAX_KEPT_BYTES / 4]);
    for index in 0..5 {
        state.keep((format!("large-{index}"), String::new()), large.clone());
    }
    assert!(state.kept.iter().map(|(_, icon)| icon.len()).sum::<usize>() <= MAX_KEPT_BYTES);
    assert_eq!(state.kept[0].0.0, "large-1");
}

fn fetched(
    status: u16,
    content_type: Option<&str>,
    length: Option<&str>,
    body: Option<&[u8]>,
) -> Fetched {
    Fetched {
        status: http::StatusCode::from_u16(status).unwrap(),
        content_type: content_type.map(str::to_owned),
        content_length: length.map(str::to_owned),
        body: body.map(Bytes::copy_from_slice),
    }
}

#[test]
fn asset_transport_enforces_status_type_length_and_exact_body() {
    let png = Some("image/png");
    assert!(admitted(fetched(200, png, Some("3"), Some(b"png"))).is_some());
    assert!(
        admitted(fetched(
            200,
            Some(" IMAGE/PNG ; charset=binary"),
            Some("0000003"),
            Some(b"png")
        ))
        .is_some()
    );
    let refusals = [
        fetched(404, png, Some("3"), Some(b"png")),
        fetched(200, Some("text/plain"), Some("3"), Some(b"png")),
        fetched(200, None, Some("3"), Some(b"png")),
        fetched(200, png, None, Some(b"png")),
        fetched(200, png, Some(""), Some(b"png")),
        fetched(200, png, Some("+3"), Some(b"png")),
        fetched(200, png, Some("00000003"), Some(b"png")),
        fetched(200, png, Some(&"9".repeat(5000)), Some(b"png")),
        fetched(200, png, Some("0"), Some(b"")),
        fetched(200, png, Some("4"), Some(b"png")),
        fetched(200, png, Some("3"), None),
        fetched(
            200,
            png,
            Some(&(MAX_ASSET_BYTES + 1).to_string()),
            Some(b"png"),
        ),
    ];
    for refused in refusals {
        assert!(admitted(refused).is_none());
    }
}

#[tokio::test]
async fn visitors_asking_for_one_cold_icon_together_share_one_read() {
    let release = Arc::new(Notify::new());
    let held = Arc::clone(&release);
    let fake = fake(move |_| Script::Held(Arc::clone(&held), ok("image/png", b"one icon"))).await;
    let icons = Arc::new(Icons::new(fake.developers.clone(), Duration::from_secs(60)));
    let visitors: Vec<_> = (0..24)
        .map(|_| {
            let icons = Arc::clone(&icons);
            tokio::spawn(async move { icons.icon(&source(1), &digest(b"one icon")).await })
        })
        .collect();
    fake.wait_active(1).await;
    for visitor in visitors {
        let mut visitor = visitor;
        loop {
            release.notify_waiters();
            if let Ok(served) = tokio::time::timeout(Duration::from_millis(20), &mut visitor).await
            {
                assert!(served.unwrap().is_some());
                break;
            }
        }
    }
    assert_eq!(fake.calls.lock().unwrap().values().sum::<usize>(), 1);
    assert!(icons.state.lock().unwrap().reading.is_empty());
}

#[tokio::test]
async fn icons_are_read_two_at_a_time_and_kept_within_their_budget() {
    let fake = fake(|target| Script::Reply(ok("image/png", target.as_bytes()))).await;
    let icons = Arc::new(Icons::new(fake.developers.clone(), Duration::from_secs(60)));
    let reads: Vec<_> = (0..12)
        .map(|index| {
            let icons = Arc::clone(&icons);
            let source = format!("{index:064x}");
            let target = format!("/api/v1/assistant-publications/sha256:{source}/icon.png");
            tokio::spawn(async move { icons.icon(&source, &digest(target.as_bytes())).await })
        })
        .collect();
    for read in reads {
        assert!(read.await.unwrap().is_some());
    }
    assert!(fake.peak.load(std::sync::atomic::Ordering::SeqCst) <= 2);
}

#[tokio::test]
async fn an_invalid_icon_head_is_refused_without_waiting_for_its_held_body() {
    use tokio::io::{AsyncReadExt, AsyncWriteExt};
    for head in [
        &b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 10\r\n\r\n"[..],
        b"HTTP/1.1 200 OK\r\nContent-Type: image/png\r\nContent-Length: 99999999\r\n\r\n",
        b"HTTP/1.1 200 OK\r\nContent-Type: image/png\r\nContent-Length: 0\r\n\r\n",
        b"HTTP/1.1 404 Not Found\r\nContent-Length: 2\r\n\r\nno",
    ] {
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let port = listener.local_addr().unwrap().port();
        let held = tokio::spawn(async move {
            let (mut stream, _) = listener.accept().await.unwrap();
            let mut request = [0; 1024];
            let _ = stream.read(&mut request).await.unwrap();
            stream.write_all(head).await.unwrap();
            tokio::time::sleep(Duration::from_secs(30)).await;
        });
        let developers = crate::catalog::upstream::Developers {
            host: "127.0.0.1".into(),
            port,
            timeout: Duration::from_secs(5),
        };
        let icons = Arc::new(Icons::new(developers, Duration::from_secs(5)));
        let started = std::time::Instant::now();
        assert_eq!(icons.icon(&source(1), &digest(b"x")).await, None);
        assert!(
            started.elapsed() < Duration::from_secs(2),
            "{:?}",
            started.elapsed()
        );
        held.abort();
    }
}
