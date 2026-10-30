//! The Store's fixed settings. Production reads nothing but `SHIMPZ_STORE_TRUSTED_PROXY_CIDRS` from its environment;
//! every other value is a constant of the deployable, and tests build their own [`Settings`].

use std::{
    net::{Ipv4Addr, SocketAddr},
    path::PathBuf,
    time::Duration,
};

/// The port the Store serves on, behind the tunnel connector.
pub const PORT: u16 = 3200;
/// The prerendered `SvelteKit` build the image ships.
pub const BUILD: &str = "/app/build";
/// The longest a connection may take to deliver a complete request head, idle keep-alive waits included.
pub const HEADER_READ_TIMEOUT: Duration = Duration::from_secs(10);
/// One deadline for draining connections and owned operations after a stop signal, below Docker's 10 s grace.
pub const SHUTDOWN_DEADLINE: Duration = Duration::from_secs(8);

/// Everything one Store process is configured with.
#[derive(Clone, Debug)]
pub struct Settings {
    /// The address the Store listens on.
    pub listen: SocketAddr,
    /// The prerendered build it serves and whose page policies it reads.
    pub build: PathBuf,
    /// The bound on reading one request head.
    pub header_read_timeout: Duration,
    /// The bound on draining after a stop signal.
    pub shutdown_deadline: Duration,
}

impl Settings {
    /// The settings of the deployed Store.
    #[must_use]
    pub fn production() -> Self {
        Self {
            listen: SocketAddr::from((Ipv4Addr::UNSPECIFIED, PORT)),
            build: PathBuf::from(BUILD),
            header_read_timeout: HEADER_READ_TIMEOUT,
            shutdown_deadline: SHUTDOWN_DEADLINE,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::Settings;

    #[test]
    fn production_serves_the_shipped_build_on_every_ipv4_interface() {
        let settings = Settings::production();
        assert_eq!(settings.listen.to_string(), "0.0.0.0:3200");
        assert_eq!(settings.build.to_str(), Some("/app/build"));
        assert_eq!(settings.header_read_timeout.as_secs(), 10);
        assert_eq!(settings.shutdown_deadline.as_secs(), 8);
    }
}
