//! The out-of-band completion page: the one-time completion code, a copy button, and nothing else.
//!
//! The document is the Python broker's byte for byte except its nonce, a fresh 24-character token that its own
//! policy names as the only style and script source. The code is `c1.<local state>.<claim>`, a broker binding and
//! hexadecimal claim joined by dots, so it needs no HTML escaping.

use http::{HeaderValue, StatusCode, header};

use super::PRIVATE_NO_STORE;
use crate::response::Reply;

/// The document's pieces around the style nonce, the code, and the script nonce.
const PIECES: [&str; 4] = [
    r#"<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Finish in Shimpz Admin</title>
  <style nonce=""#,
    r#"">
    :root { color-scheme: dark; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    * { box-sizing: border-box; }
    body { min-height: 100vh; margin: 0; display: grid; place-items: center; background: #000; color: #f4f4f5; }
    main { width: min(50rem, calc(100% - 2rem)); border: 1px solid #303036; padding: clamp(1.5rem, 5vw, 3rem); }
    p { color: #a1a1aa; line-height: 1.6; }
    label { display: block; margin: 2rem 0 .6rem; color: #00e5f0; font-size: .8rem; letter-spacing: .12em; }
    input { width: 100%; padding: 1rem; border: 1px solid #3f3f46; background: #09090b; color: #fff; font: inherit; }
    button { width: 100%; margin-top: .75rem; padding: 1rem; border: 0; background: #00e5f0; color: #000;
      font: 700 1rem inherit; cursor: pointer; }
    .warning { color: #f4f4f5; }
  </style>
</head>
<body>
  <main>
    <p>INTEGRATION // ONE-TIME COMPLETION</p>
    <h1>Finish in your original Shimpz Admin tab.</h1>
    <p>Copy this short-lived code, return to the tab that started Cloudflare authorization, and paste it there.</p>
    <label for="completion-code">COMPLETION CODE</label>
    <input id="completion-code" value=""#,
    r#"" readonly autocomplete="off" spellcheck="false">
    <button id="copy-code" type="button">COPY CODE</button>
    <p class="warning">Do not paste this code into chat or another site. It contains no provider token and works
      only with the Admin session that started this authorization.</p>
  </main>
  <script nonce=""#,
    r#"">
    const input = document.getElementById('completion-code');
    const button = document.getElementById('copy-code');
    button.addEventListener('click', async () => {
      input.select();
      try {
        await navigator.clipboard.writeText(input.value);
        button.textContent = 'COPIED';
      } catch (_error) {
        button.textContent = 'SELECTED — COPY MANUALLY';
      }
    });
  </script>
</body>
</html>"#,
];

/// The completion page for `code` under `nonce`.
///
/// # Panics
///
/// When `nonce` is not a header-safe token; the broker's nonces are base64url.
#[must_use]
pub fn completion_page(code: &str, nonce: &str) -> Reply {
    let document = [
        PIECES[0], nonce, PIECES[1], code, PIECES[2], nonce, PIECES[3],
    ]
    .concat();
    let policy = format!(
        "default-src 'none'; style-src 'nonce-{nonce}'; script-src 'nonce-{nonce}'; base-uri 'none'; \
         form-action 'none'; frame-ancestors 'none'; require-trusted-types-for 'script'; trusted-types 'none'"
    );
    let headers = vec![
        (header::CACHE_CONTROL, PRIVATE_NO_STORE),
        (
            header::REFERRER_POLICY,
            HeaderValue::from_static("no-referrer"),
        ),
        (
            header::CONTENT_SECURITY_POLICY,
            HeaderValue::from_str(&policy).expect("a nonce is base64url"),
        ),
        (
            http::HeaderName::from_static("cross-origin-opener-policy"),
            HeaderValue::from_static("same-origin"),
        ),
        (
            header::X_CONTENT_TYPE_OPTIONS,
            HeaderValue::from_static("nosniff"),
        ),
    ];
    Reply::new(
        StatusCode::OK,
        headers,
        Some("text/html; charset=utf-8"),
        document,
    )
}

#[cfg(test)]
mod tests {
    use http::StatusCode;

    use super::completion_page;

    #[test]
    fn the_page_is_the_python_brokers_byte_for_byte_with_its_own_policy() {
        let code = format!("c1.{}.{}", "s".repeat(43), "a".repeat(64));
        let reply = completion_page(&code, &"N".repeat(24));
        assert_eq!(reply.status, StatusCode::OK);
        assert_eq!(&reply.body[..], include_bytes!("completion/expected.html"));
        let headers: Vec<_> = reply
            .headers
            .iter()
            .map(|(name, value)| (name.as_str(), value.to_str().unwrap().to_owned()))
            .collect();
        let nonce = "N".repeat(24);
        assert_eq!(
            headers,
            [
                ("cache-control", "private, no-store".to_owned()),
                ("referrer-policy", "no-referrer".to_owned()),
                (
                    "content-security-policy",
                    format!(
                        "default-src 'none'; style-src 'nonce-{nonce}'; script-src 'nonce-{nonce}'; \
                         base-uri 'none'; form-action 'none'; frame-ancestors 'none'; \
                         require-trusted-types-for 'script'; trusted-types 'none'"
                    )
                ),
                ("cross-origin-opener-policy", "same-origin".to_owned()),
                ("x-content-type-options", "nosniff".to_owned()),
                ("content-length", "2268".to_owned()),
                ("content-type", "text/html; charset=utf-8".to_owned()),
            ]
        );
    }
}
