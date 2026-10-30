//! The `shimpz-store` command line: serve plain HTTP, serve TLS from PEM files, or check a running Store's health.

use std::{ffi::OsString, path::PathBuf};

/// The usage line a refused command line prints.
pub const USAGE: &str = "usage: shimpz-store [healthcheck | --tls-certificate PATH --tls-key PATH]";

/// The PEM certificate chain and private key a TLS Store serves with.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct TlsFiles {
    /// The certificate chain, leaf first.
    pub certificate: PathBuf,
    /// The private key.
    pub key: PathBuf,
}

/// What one invocation does.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Command {
    /// Serve until SIGTERM, over TLS when given its files.
    Serve(Option<TlsFiles>),
    /// Check the local Store's health once.
    Healthcheck,
}

/// The command the arguments name: none, `healthcheck`, or both TLS flags with their paths in this order.
#[must_use]
pub fn parse(arguments: &[OsString]) -> Option<Command> {
    match arguments {
        [] => Some(Command::Serve(None)),
        [only] if only == "healthcheck" => Some(Command::Healthcheck),
        [certificate_flag, certificate, key_flag, key]
            if certificate_flag == "--tls-certificate" && key_flag == "--tls-key" =>
        {
            Some(Command::Serve(Some(TlsFiles {
                certificate: PathBuf::from(certificate),
                key: PathBuf::from(key),
            })))
        }
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use std::{ffi::OsString, path::PathBuf};

    use super::{Command, TlsFiles, parse};

    fn arguments(words: &[&str]) -> Vec<OsString> {
        words.iter().map(OsString::from).collect()
    }

    #[test]
    fn only_the_three_command_lines_parse() {
        assert_eq!(parse(&[]), Some(Command::Serve(None)));
        assert_eq!(
            parse(&arguments(&["healthcheck"])),
            Some(Command::Healthcheck)
        );
        assert_eq!(
            parse(&arguments(&[
                "--tls-certificate",
                "c.pem",
                "--tls-key",
                "k.pem"
            ])),
            Some(Command::Serve(Some(TlsFiles {
                certificate: PathBuf::from("c.pem"),
                key: PathBuf::from("k.pem"),
            })))
        );
        for refused in [
            &["serve"][..],
            &["healthcheck", "x"],
            &["--tls-key", "k.pem", "--tls-certificate", "c.pem"],
            &["--tls-certificate", "c.pem", "--tls-cert", "k.pem"],
            &["--tls-certificate", "c.pem"],
        ] {
            assert_eq!(parse(&arguments(refused)), None, "{refused:?}");
        }
    }
}
