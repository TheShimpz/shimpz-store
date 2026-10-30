//! Python's `urllib.parse` decoding of the request target and of query strings, as the Python Store applied it.

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

/// A query string strict parsing refuses.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct InvalidQuery;

/// `urllib.parse.parse_qsl(query, keep_blank_values=True, strict_parsing=strict, max_num_fields=max_fields)`.
///
/// The query splits on `&`; with `max_fields`, more than that many segments refuse it. An empty segment is skipped,
/// or refused when strict; a segment without `=` refuses a strict parse and is otherwise a name with an empty value.
/// Names and values turn `+` into a space and are then [`unquote`]d.
///
/// # Errors
///
/// Too many fields, or, when strict, an empty segment or one without `=`.
pub fn parse_qsl(
    query: &str,
    strict: bool,
    max_fields: Option<usize>,
) -> Result<Vec<(String, String)>, InvalidQuery> {
    if query.is_empty() {
        return Ok(Vec::new());
    }
    let fields = query.matches('&').count() + 1;
    if max_fields.is_some_and(|max_fields| max_fields < fields) {
        return Err(InvalidQuery);
    }
    let mut pairs = Vec::new();
    for segment in query.split('&') {
        if segment.is_empty() && !strict {
            continue;
        }
        let (name, value) = match segment.split_once('=') {
            Some(pair) => pair,
            None if strict => return Err(InvalidQuery),
            None => (segment, ""),
        };
        pairs.push((unquote_plus(name), unquote_plus(value)));
    }
    Ok(pairs)
}

fn unquote_plus(text: &str) -> String {
    unquote(&text.replace('+', " ")).into_owned()
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
    use super::{InvalidQuery, parse_qsl, unquote};

    fn pairs(
        query: &str,
        strict: bool,
        max_fields: Option<usize>,
    ) -> Result<Vec<(String, String)>, InvalidQuery> {
        parse_qsl(query, strict, max_fields)
    }

    fn owned(pairs: &[(&str, &str)]) -> Vec<(String, String)> {
        pairs
            .iter()
            .map(|(name, value)| ((*name).to_owned(), (*value).to_owned()))
            .collect()
    }

    #[test]
    fn a_lenient_parse_keeps_blank_values_and_names_without_values() {
        assert_eq!(pairs("", false, None), Ok(Vec::new()));
        assert_eq!(
            pairs("a=1&&b&c=&=d&a=%41+b%2B&e=f=g", false, None),
            Ok(owned(&[
                ("a", "1"),
                ("b", ""),
                ("c", ""),
                ("", "d"),
                ("a", "A b+"),
                ("e", "f=g")
            ]))
        );
        assert_eq!(pairs("&", false, None), Ok(Vec::new()));
        assert_eq!(
            pairs("n%C3=%zz", false, None),
            Ok(owned(&[("n\u{fffd}", "%zz")]))
        );
    }

    #[test]
    fn a_strict_parse_refuses_empty_segments_and_segments_without_a_value_separator() {
        assert_eq!(
            pairs("a=1&b=", true, None),
            Ok(owned(&[("a", "1"), ("b", "")]))
        );
        for refused in ["a=1&", "&a=1", "a=1&&b=2", "a", "a=1&b"] {
            assert_eq!(pairs(refused, true, None), Err(InvalidQuery), "{refused}");
        }
    }

    #[test]
    fn more_segments_than_the_maximum_refuse_the_query() {
        assert_eq!(
            pairs("a=1&b=2", false, Some(2)).map(|pairs| pairs.len()),
            Ok(2)
        );
        assert_eq!(pairs("a=1&b=2&", false, Some(2)), Err(InvalidQuery));
        assert_eq!(pairs("", true, Some(0)), Ok(Vec::new()));
    }

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
