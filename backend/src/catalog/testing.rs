//! A scripted Developers for the catalog and icon tests: it answers each request with the bytes its script gives
//! for the target, optionally held until released, and counts calls and peak concurrency.

use std::{
    collections::HashMap,
    sync::{
        Arc, Mutex,
        atomic::{AtomicUsize, Ordering},
    },
    time::Duration,
};

use tokio::{
    io::{AsyncReadExt, AsyncWriteExt},
    net::TcpListener,
    sync::Notify,
};

use super::upstream::Developers;

/// What the scripted Developers does with one request.
pub enum Script {
    /// Answer these bytes at once.
    Reply(Vec<u8>),
    /// Answer these bytes once the notify is released.
    Held(Arc<Notify>, Vec<u8>),
}

/// The scripted Developers and what it observed.
pub struct Fake {
    pub developers: Developers,
    pub calls: Calls,
    pub active: Arc<AtomicUsize>,
    pub peak: Arc<AtomicUsize>,
}

impl Fake {
    pub fn calls(&self, target: &str) -> usize {
        self.calls
            .lock()
            .unwrap()
            .get(target)
            .copied()
            .unwrap_or_default()
    }

    /// Wait until `count` requests are being answered at once.
    pub async fn wait_active(&self, count: usize) {
        while self.active.load(Ordering::SeqCst) < count {
            tokio::time::sleep(Duration::from_millis(5)).await;
        }
    }
}

pub fn ok(content_type: &str, body: &[u8]) -> Vec<u8> {
    let head = format!(
        "HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {}\r\n\r\n",
        body.len()
    );
    [head.as_bytes(), body].concat()
}

type Calls = Arc<Mutex<HashMap<String, usize>>>;

async fn answer(
    mut stream: tokio::net::TcpStream,
    script: Arc<dyn Fn(&str) -> Script + Send + Sync>,
    calls: Calls,
    active: Arc<AtomicUsize>,
    peak: Arc<AtomicUsize>,
) {
    let mut head = Vec::new();
    let mut buffer = [0; 1024];
    while !head.windows(4).any(|window| window == b"\r\n\r\n") {
        let read = stream.read(&mut buffer).await.unwrap();
        head.extend_from_slice(&buffer[..read]);
    }
    let target = String::from_utf8_lossy(&head)
        .split(' ')
        .nth(1)
        .unwrap()
        .to_owned();
    *calls.lock().unwrap().entry(target.clone()).or_default() += 1;
    let now = active.fetch_add(1, Ordering::SeqCst) + 1;
    peak.fetch_max(now, Ordering::SeqCst);
    let reply = match script(&target) {
        Script::Reply(bytes) => bytes,
        Script::Held(release, bytes) => {
            release.notified().await;
            bytes
        }
    };
    active.fetch_sub(1, Ordering::SeqCst);
    let _ = stream.write_all(&reply).await;
}

pub async fn fake(script: impl Fn(&str) -> Script + Send + Sync + 'static) -> Fake {
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = listener.local_addr().unwrap().port();
    let script: Arc<dyn Fn(&str) -> Script + Send + Sync> = Arc::new(script);
    let calls = Arc::new(Mutex::new(HashMap::new()));
    let (active, peak) = (Arc::new(AtomicUsize::new(0)), Arc::new(AtomicUsize::new(0)));
    let observed = (Arc::clone(&calls), Arc::clone(&active), Arc::clone(&peak));
    tokio::spawn(async move {
        loop {
            let (stream, _) = listener.accept().await.unwrap();
            let (script, (calls, active, peak)) = (
                Arc::clone(&script),
                (
                    Arc::clone(&observed.0),
                    Arc::clone(&observed.1),
                    Arc::clone(&observed.2),
                ),
            );
            tokio::spawn(answer(stream, script, calls, active, peak));
        }
    });
    Fake {
        developers: Developers {
            host: "127.0.0.1".into(),
            port,
            timeout: Duration::from_secs(5),
        },
        calls,
        active,
        peak,
    }
}
