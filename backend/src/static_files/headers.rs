//! A build file's response headers: its closed media type, its integer entity tag, and its Last-Modified date.

use crate::date::imf_fixdate;

const OPAQUE: &str = "application/octet-stream";
const MEDIA_TYPES: [(&str, &str); 12] = [
    (".html", "text/html; charset=utf-8"),
    (".css", "text/css; charset=utf-8"),
    (".js", "text/javascript; charset=utf-8"),
    (".json", "application/json"),
    (".png", "image/png"),
    (".svg", "image/svg+xml"),
    (".txt", "text/plain; charset=utf-8"),
    (".xml", "text/xml; charset=utf-8"),
    (".woff", "font/woff"),
    (".woff2", "font/woff2"),
    (".ico", "image/vnd.microsoft.icon"),
    (".webmanifest", "application/manifest+json"),
];
const NANOS_PER_SECOND: i128 = 1_000_000_000;

/// A file name's suffix as Python's `PurePath.suffix` reads it, ASCII-lowercased: from its last `.`, unless the
/// name has no dot or only a leading one.
#[must_use]
pub fn suffix(name: &str) -> String {
    match name.rfind('.') {
        Some(index) if index > 0 => name[index..].to_ascii_lowercase(),
        _ => String::new(),
    }
}

/// The exact `Content-Type` of a build file by its name; any other suffix is opaque bytes.
#[must_use]
pub fn media_type(name: &str) -> &'static str {
    let suffix = suffix(name);
    MEDIA_TYPES
        .iter()
        .find(|(known, _)| *known == suffix)
        .map_or(OPAQUE, |(_, media_type)| media_type)
}

/// `"<mtime_ns hex>-<size hex>"`, each in lowercase sign-magnitude hexadecimal.
#[must_use]
pub fn entity_tag(mtime_ns: i128, size: u64) -> String {
    let sign = if mtime_ns < 0 { "-" } else { "" };
    format!("\"{sign}{:x}-{size:x}\"", mtime_ns.unsigned_abs())
}

/// The file's whole mtime second as an IMF-fixdate, floored, or `None` outside the years the format names.
#[must_use]
pub fn last_modified(mtime_ns: i128) -> Option<String> {
    i64::try_from(mtime_ns.div_euclid(NANOS_PER_SECOND))
        .ok()
        .and_then(imf_fixdate)
}

#[cfg(test)]
mod tests {
    use super::{entity_tag, last_modified, media_type, suffix};

    #[test]
    fn the_suffix_follows_python_purepath() {
        let cases = [
            ("a.JS", ".js"),
            ("a.tar.gz", ".gz"),
            ("a..js", ".js"),
            ("a.", "."),
            (".js", ""),
            ("plain", ""),
            ("a. js", ". js"),
        ];
        for (name, expected) in cases {
            assert_eq!(suffix(name), expected, "{name}");
        }
    }

    #[test]
    fn every_build_file_kind_has_its_closed_media_type() {
        let cases = [
            ("page.html", "text/html; charset=utf-8"),
            ("UPPER.JS", "text/javascript; charset=utf-8"),
            ("sitemap.xml", "text/xml; charset=utf-8"),
            ("font.woff2", "font/woff2"),
            ("app.webmanifest", "application/manifest+json"),
            ("chunk.js.map", "application/octet-stream"),
            ("legacy.htm", "application/octet-stream"),
            ("trailing.", "application/octet-stream"),
            (".js", "application/octet-stream"),
        ];
        for (name, expected) in cases {
            assert_eq!(media_type(name), expected, "{name}");
        }
    }

    #[test]
    fn the_entity_tag_names_the_integer_mtime_and_size() {
        assert_eq!(entity_tag(0, 0), "\"0-0\"");
        assert_eq!(entity_tag(1, 1), "\"1-1\"");
        assert_eq!(
            entity_tag(1_700_000_000_000_000_000, 4096),
            "\"17979cfe362a0000-1000\""
        );
        assert_eq!(entity_tag(-1, 1 << 40), "\"-1-10000000000\"");
        assert_eq!(entity_tag(-1_000_000_001, 3), "\"-3b9aca01-3\"");
        assert_eq!(
            entity_tag(i128::from(i64::MIN) * 1_000_000_000, 0),
            "\"-1dcd65000000000000000000-0\""
        );
    }

    #[test]
    fn last_modified_floors_the_mtime_to_its_whole_second_within_four_digit_years() {
        let day = "Tue, 14 Nov 2023 22:13:20 GMT";
        for mtime_ns in [
            1_700_000_000_000_000_000,
            1_700_000_000_999_999_000,
            1_700_000_000_999_999_500,
            1_700_000_000_999_999_999,
        ] {
            assert_eq!(last_modified(mtime_ns).as_deref(), Some(day));
        }
        assert_eq!(
            last_modified(1_700_000_001_000_000_000).as_deref(),
            Some("Tue, 14 Nov 2023 22:13:21 GMT")
        );
        assert_eq!(last_modified(-1), None);
        assert_eq!(last_modified(-1_000_000_000), None);
        assert_eq!(
            last_modified(0).as_deref(),
            Some("Thu, 01 Jan 1970 00:00:00 GMT")
        );
        assert_eq!(last_modified(i128::MAX), None);
    }
}
