//! `shimpz-store`: serve the platform Store.

use std::process::ExitCode;

fn main() -> ExitCode {
    let arguments: Vec<_> = std::env::args_os().skip(1).collect();
    store_backend::run(&arguments, &store_backend::config::Settings::production())
}
