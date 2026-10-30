//! The Store's log: one JSON object per line on stdout, `{"ts","level","service","msg", ...fields}` as the Python
//! Store wrote it, with a closed event code as `msg` and fields that are closed codes or request paths, never a query
//! value, body, header, token, secret, or foreign error text. A panic is logged by its location only.

use std::{
    fmt::Write as _,
    io::{self, Write},
    panic::PanicHookInfo,
    time::{SystemTime, UNIX_EPOCH},
};

use crate::date::rfc3339_micros;

const SERVICE: &str = "shimpz-store";

/// How severe an event is.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Level {
    /// The Store could not do what it must, such as start or answer a request.
    Error,
    /// A request was refused or an upstream failed.
    Warning,
}

/// Write one event to stdout.
pub fn event(level: Level, code: &str, fields: &[(&str, &str)]) {
    let _unwritable = writeln!(
        io::stdout(),
        "{}",
        line(SystemTime::now(), level, code, fields)
    );
}

/// One event's log line at `at`.
#[must_use]
pub fn line(at: SystemTime, level: Level, code: &str, fields: &[(&str, &str)]) -> String {
    let since_epoch = at.duration_since(UNIX_EPOCH).unwrap_or_default();
    let level = match level {
        Level::Error => "error",
        Level::Warning => "warning",
    };
    let mut line = format!(
        "{{\"ts\":\"{}\",\"level\":\"{level}\",\"service\":\"{SERVICE}\",\"msg\":",
        rfc3339_micros(since_epoch)
    );
    quote(code, &mut line);
    for (name, value) in fields {
        line.push(',');
        quote(name, &mut line);
        line.push(':');
        quote(value, &mut line);
    }
    line.push('}');
    line
}

/// Append `text` as a JSON string: `"` and `\` escaped, every character below U+0020 as `\u00XX`.
fn quote(text: &str, out: &mut String) {
    out.push('"');
    for character in text.chars() {
        match character {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            control if u32::from(control) < 0x20 => {
                let _infallible = write!(out, "\\u{:04x}", u32::from(control));
            }
            other => out.push(other),
        }
    }
    out.push('"');
}

/// Replace the default panic hook, which prints the payload to stderr, by one JSON line with the location only.
pub fn install_panic_hook() {
    std::panic::set_hook(Box::new(|info| {
        let _unwritable = writeln!(io::stdout(), "{}", panic_line(info));
    }));
}

/// The log line of one panic: its source location, never its payload.
#[must_use]
pub fn panic_line(info: &PanicHookInfo<'_>) -> String {
    let location = info.location().map_or_else(String::new, |location| {
        format!("{}:{}", location.file(), location.line())
    });
    let mut line = String::from("{\"level\":\"ERROR\",\"msg\":\"panic\",\"location\":");
    quote(&location, &mut line);
    line.push('}');
    line
}

#[cfg(test)]
mod tests;
