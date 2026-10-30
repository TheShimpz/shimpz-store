//! Python's `urllib.parse` decoding of the request target, as the Python Store's server and framework applied it.

use std::borrow::Cow;

/// `urllib.parse.unquote(text)` of an ASCII request path: every `%XX` with two hexadecimal digits becomes its byte,
/// any other `%` stays, and the bytes are read as UTF-8 with each invalid sequence replaced by U+FFFD.
#[must_use]
pub fn unquote(text: &str) -> Cow<'_, str> {
    if !text.contains('%') {
        return Cow::Borrowed(text);
    }
    let bytes = text.as_bytes();
    let mut decoded = Vec::with_capacity(bytes.len());
    let mut index = 0;
    while index < bytes.len() {
        if let Some(byte) = escaped(bytes, index) {
            decoded.push(byte);
            index += 3;
        } else {
            decoded.push(bytes[index]);
            index += 1;
        }
    }
    Cow::Owned(String::from_utf8_lossy(&decoded).into_owned())
}

/// The byte a `%XX` escape at `index` names.
fn escaped(bytes: &[u8], index: usize) -> Option<u8> {
    if bytes[index] != b'%' {
        return None;
    }
    let high = hex(*bytes.get(index + 1)?)?;
    let low = hex(*bytes.get(index + 2)?)?;
    Some(high << 4 | low)
}

fn hex(byte: u8) -> Option<u8> {
    char::from(byte)
        .to_digit(16)
        .and_then(|digit| u8::try_from(digit).ok())
}

#[cfg(test)]
mod tests {
    use super::unquote;

    #[test]
    fn unquote_decodes_valid_escapes_to_utf8_and_keeps_the_rest() {
        let cases = [
            ("/en", "/en"),
            ("/%65n", "/en"),
            ("/en%2Fabout", "/en/about"),
            ("/a%2fb%2E%2e", "/a/b.."),
            ("/%zz%4", "/%zz%4"),
            ("/%", "/%"),
            ("/%C3%A9", "/\u{e9}"),
            ("/%C3", "/\u{fffd}"),
            ("/%C3x", "/\u{fffd}x"),
            ("/%E2%82", "/\u{fffd}"),
            ("/%FF%FE", "/\u{fffd}\u{fffd}"),
            ("/%00%0a", "/\0\n"),
        ];
        for (raw, expected) in cases {
            assert_eq!(unquote(raw), expected, "{raw}");
        }
    }
}
