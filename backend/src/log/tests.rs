use std::{
    panic,
    sync::{Arc, Mutex, PoisonError},
    time::{Duration, UNIX_EPOCH},
};

use super::{Level, event, install_panic_hook, line, panic_line};

/// The panic hook is one per process: the tests that replace it take turns.
static HOOK: Mutex<()> = Mutex::new(());

#[test]
fn the_server_loggers_write_only_json_templates_on_stdout() {
    let at = UNIX_EPOCH + Duration::new(1_700_000_000, 5_000);
    assert_eq!(
        line(
            at,
            Level::Warning,
            "oauth_broker_rejected",
            &[("operation", "start")]
        ),
        "{\"ts\":\"2023-11-14T22:13:20.000005Z\",\"level\":\"warning\",\"service\":\"shimpz-store\",\
         \"msg\":\"oauth_broker_rejected\",\"operation\":\"start\"}"
    );
    let escaped = line(
        UNIX_EPOCH,
        Level::Error,
        "unhandled_exception",
        &[("path", "/a\"b\\c\n\u{1}é\u{7f}")],
    );
    assert!(
        escaped.ends_with("\"path\":\"/a\\\"b\\\\c\\u000a\\u0001é\u{7f}\"}"),
        "{escaped}"
    );
    assert!(escaped.contains("\"level\":\"error\""));
    event(Level::Warning, "store_capacity_rejected", &[("path", "/x")]);
}

#[test]
fn the_panic_hook_logs_the_location_and_never_the_payload() {
    let _turn = HOOK.lock().unwrap_or_else(PoisonError::into_inner);
    let lines = Arc::new(Mutex::new(Vec::new()));
    let sink = Arc::clone(&lines);
    let previous = panic::take_hook();
    panic::set_hook(Box::new(move |info| {
        sink.lock().unwrap().push(panic_line(info));
    }));
    let caught = panic::catch_unwind(|| panic!("PRIVATE_SENTINEL"));
    panic::set_hook(previous);
    assert!(caught.is_err());
    let lines = lines.lock().unwrap();
    assert!(lines.iter().all(|line| !line.contains("PRIVATE_SENTINEL")));
    assert!(lines.iter().any(|line| {
        line.starts_with("{\"level\":\"ERROR\",\"msg\":\"panic\",\"location\":\"src/log/tests.rs:")
    }));
}

#[test]
fn the_installed_hook_writes_its_line() {
    let _turn = HOOK.lock().unwrap_or_else(PoisonError::into_inner);
    let previous = panic::take_hook();
    install_panic_hook();
    let caught = panic::catch_unwind(|| panic!("PRIVATE_SENTINEL"));
    panic::set_hook(previous);
    assert!(caught.is_err());
}

#[test]
fn every_exception_form_is_summarized_by_its_class() {
    use crate::catalog::upstream::Failure;
    for failure in [Failure::Connect, Failure::TimedOut, Failure::Protocol] {
        let line = super::line(
            std::time::SystemTime::UNIX_EPOCH,
            super::Level::Warning,
            "proxy_unreachable",
            &[("error", failure.code())],
        );
        assert!(
            line.ends_with(&format!(",\"error\":\"{}\"}}", failure.code())),
            "{line}"
        );
    }
}

#[test]
fn logged_exceptions_never_render_frame_locals() {
    let _turn = HOOK.lock().unwrap_or_else(PoisonError::into_inner);
    let lines = Arc::new(Mutex::new(Vec::new()));
    let sink = Arc::clone(&lines);
    let previous = panic::take_hook();
    panic::set_hook(Box::new(move |info| {
        sink.lock().unwrap().push(panic_line(info));
    }));
    let local_secret = String::from("PRIVATE_LOCAL_VALUE");
    let caught = panic::catch_unwind(|| panic!("failed with {local_secret}"));
    panic::set_hook(previous);
    assert!(caught.is_err());
    let lines = lines.lock().unwrap();
    let line = lines.first().unwrap();
    assert!(
        !line.contains("PRIVATE_LOCAL_VALUE") && !line.contains("failed with"),
        "{line}"
    );
    let keys: Vec<&str> = line
        .split("\":")
        .map(|part| part.rsplit('"').next().unwrap())
        .collect();
    assert_eq!(keys[..3], ["level", "msg", "location"]);
}
