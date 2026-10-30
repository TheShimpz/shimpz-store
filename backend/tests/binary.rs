//! The built `shimpz-store` binary's command line.

use std::process::Command;

#[test]
fn an_unknown_argument_is_a_usage_error_written_as_one_json_line() {
    let output = Command::new(env!("CARGO_BIN_EXE_shimpz-store"))
        .arg("serve")
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(2));
    assert_eq!(output.stdout, b"");
    let stderr = String::from_utf8(output.stderr).unwrap();
    assert_eq!(stderr.lines().count(), 1);
    assert!(
        stderr.starts_with("{\"level\":\"ERROR\",\"msg\":\"usage: shimpz-store"),
        "{stderr}"
    );
}
