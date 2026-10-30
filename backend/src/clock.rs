//! The one place the Store reads time: a monotonic reading for every lifetime and cache, and the wall clock's whole
//! seconds for lease expiry. Tests replace it with a clock they step by hand.

use std::{
    sync::atomic::{AtomicU64, Ordering},
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

/// A source of time.
pub trait Clock: Send + Sync {
    /// Time elapsed on a monotonic clock since an arbitrary origin.
    fn monotonic(&self) -> Duration;
    /// Whole seconds since the Unix epoch on the wall clock (`int(time.time())`).
    fn wall_seconds(&self) -> i64;
}

/// The operating system's clocks.
#[derive(Debug)]
pub struct SystemClock {
    origin: Instant,
}

impl SystemClock {
    /// A system clock whose monotonic origin is now.
    #[must_use]
    pub fn new() -> Self {
        Self {
            origin: Instant::now(),
        }
    }
}

impl Default for SystemClock {
    fn default() -> Self {
        Self::new()
    }
}

impl Clock for SystemClock {
    fn monotonic(&self) -> Duration {
        self.origin.elapsed()
    }

    fn wall_seconds(&self) -> i64 {
        let since = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default();
        i64::try_from(since.as_secs()).unwrap_or(i64::MAX)
    }
}

/// A clock that moves only when a test steps it: both readings advance together.
#[derive(Debug, Default)]
pub struct ManualClock {
    nanos: AtomicU64,
    wall: AtomicU64,
}

impl ManualClock {
    /// A manual clock at wall second `wall`.
    #[must_use]
    pub fn at(wall: u64) -> Self {
        Self {
            nanos: AtomicU64::new(0),
            wall: AtomicU64::new(wall),
        }
    }

    /// Move both readings forward by `by`.
    pub fn step(&self, by: Duration) {
        self.nanos.fetch_add(
            u64::try_from(by.as_nanos()).unwrap_or(u64::MAX),
            Ordering::SeqCst,
        );
        self.wall.fetch_add(by.as_secs(), Ordering::SeqCst);
    }
}

impl Clock for ManualClock {
    fn monotonic(&self) -> Duration {
        Duration::from_nanos(self.nanos.load(Ordering::SeqCst))
    }

    fn wall_seconds(&self) -> i64 {
        i64::try_from(self.wall.load(Ordering::SeqCst)).unwrap_or(i64::MAX)
    }
}

#[cfg(test)]
mod tests {
    use std::time::Duration;

    use super::{Clock, SystemClock};

    #[test]
    fn the_system_clock_moves_forward_from_now() {
        let clock = SystemClock::default();
        assert!(clock.monotonic() < Duration::from_secs(60));
        assert!(clock.wall_seconds() > 1_700_000_000);
    }
}
