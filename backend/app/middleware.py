"""Bind a request trace ID into structlog context variables.

Every log line for the request carries the ID across nested calls. The middleware reuses an inbound
X-Request-ID propagated by a caller or mints one, then echoes it so a browser or calling service can
follow the same request end-to-end.

The inbound header is ATTACKER-CONTROLLED, so it is never trusted raw: it flows into a response header (a
control byte would crash the ASGI send / enable header injection) and into contextvars + every log line (an
oversized value would bloat them). _clean() decodes safely (latin-1 never raises on bad bytes), keeps only a
conservative token charset, and caps the length — an empty/oversized/hostile ID is replaced with a fresh one.

The middleware is also the only author of the browser security headers. Its script policy admits this origin and the
exact inline bootstrap scripts of the prerendered build, by hash, never 'unsafe-inline'; the OAuth completion page
alone keeps the nonce policy its route sets.
"""

import base64
import functools
import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path
from uuid import uuid4

import structlog

from app.config import BUILD

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")
_CSP_PREFIX = b"default-src 'self'; base-uri 'self'; object-src 'none'; "
_CSP_STYLE_AND_REST = (
    b"style-src 'self' 'unsafe-inline'; "
    b"img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https: wss:; "
    b"frame-src 'none'; "
    b"worker-src 'self' blob:; manifest-src 'self'; upgrade-insecure-requests"
)
_EMBED_ANCESTORS = b"frame-ancestors http://127.0.0.1:* http://localhost:* http://[::1]:* https://local.shimpz.com; "
_COMMON_SECURITY_HEADERS = (
    (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (
        b"permissions-policy",
        b"camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    ),
)
_MANAGED_SECURITY_HEADERS = {
    *(name for name, _value in _COMMON_SECURITY_HEADERS),
    b"content-security-policy",
    b"x-frame-options",
    b"x-robots-tag",
}


class _InlineScriptCollector(HTMLParser):
    """Collect the text of every inline script, the only scripts SvelteKit's prerendered pages carry inline."""

    def __init__(self) -> None:
        super().__init__()
        self._collecting = False
        self._chunks: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._collecting = tag == "script" and "src" not in dict(attrs)
        if self._collecting:
            self._chunks = []

    def handle_data(self, data: str) -> None:
        if self._collecting:
            self._chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._collecting:
            self.scripts.append("".join(self._chunks))
            self._collecting = False


def build_script_sources(build: Path) -> tuple[bytes, ...]:
    """The hash source of every distinct inline script of the prerendered build, in one stable order.

    Only the immutable build the image ships is hashed, never a response body, so no reflected script can ever be
    admitted; a build without inline scripts, or no build, admits scripts from this origin only.
    """
    sources = set()
    for document in sorted(build.rglob("*.html")):
        collector = _InlineScriptCollector()
        collector.feed(document.read_text(encoding="utf-8"))
        collector.close()
        for script in collector.scripts:
            digest = base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest())
            sources.add(b"'sha256-" + digest + b"'")
    return tuple(sorted(sources))


@functools.cache
def security_headers(build: Path) -> tuple[tuple[tuple[bytes, bytes], ...], tuple[tuple[bytes, bytes], ...]]:
    """The page and Admin-embed header sets: one script policy bound to the build's exact inline scripts."""
    script_policy = b"script-src " + b" ".join((b"'self'", *build_script_sources(build))) + b"; "
    suffix = b"form-action 'self'; " + script_policy + _CSP_STYLE_AND_REST
    page = (
        _COMMON_SECURITY_HEADERS[0],
        (b"content-security-policy", _CSP_PREFIX + b"frame-ancestors 'none'; " + suffix),
        _COMMON_SECURITY_HEADERS[1],
        (b"x-frame-options", b"DENY"),
        _COMMON_SECURITY_HEADERS[2],
        _COMMON_SECURITY_HEADERS[3],
    )
    embed = (
        _COMMON_SECURITY_HEADERS[0],
        (b"content-security-policy", _CSP_PREFIX + _EMBED_ANCESTORS + suffix),
        _COMMON_SECURITY_HEADERS[1],
        _COMMON_SECURITY_HEADERS[2],
        _COMMON_SECURITY_HEADERS[3],
        (b"x-robots-tag", b"noindex, nofollow"),
    )
    return page, embed


_EMBED_PATH = re.compile(r"^/(?:en|pt|es|zh|fr|de|ja|ar)/assistants/embed/?$")
_NO_REFERRER_PATHS = frozenset(
    {
        "/api/oauth/cloudflare/start",
        "/api/oauth/cloudflare/callback",
    }
)
_RESPONSE_CSP_PATHS = frozenset({"/api/oauth/cloudflare/callback"})


def _security_headers(path: str) -> tuple[tuple[bytes, bytes], ...]:
    page, embed = security_headers(BUILD)
    headers = embed if _EMBED_PATH.fullmatch(path) else page
    if path not in _NO_REFERRER_PATHS:
        return headers
    return tuple((name, b"no-referrer") if name == b"referrer-policy" else (name, value) for name, value in headers)


def _clean(raw: bytes) -> str:
    tid = _UNSAFE.sub("", raw.decode("latin-1"))[:200]  # strip non-token chars (drops CTLs/unicode), cap 200
    return tid or uuid4().hex  # empty after cleaning → mint a safe one


class TraceIdMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        trace_id = _clean(headers.get(b"x-request-id", b""))
        # Bind WITHOUT reset: each request runs in its own contextvars copy (can't leak across requests),
        # and the id must stay visible to the exception handler in the outer error middleware.
        structlog.contextvars.bind_contextvars(trace_id=trace_id)
        security_headers = _security_headers(scope.get("path", ""))

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                response_headers = message.get("headers") or []
                response_csp = next(
                    (value for name, value in response_headers if name.lower() == b"content-security-policy"),
                    None,
                )
                selected_headers = security_headers
                if scope.get("path", "") in _RESPONSE_CSP_PATHS and response_csp is not None:
                    selected_headers = tuple(
                        (name, response_csp) if name == b"content-security-policy" else (name, value)
                        for name, value in security_headers
                    )
                managed = _MANAGED_SECURITY_HEADERS | {b"x-request-id"}
                message["headers"] = [(name, value) for name, value in response_headers if name.lower() not in managed]
                message["headers"].extend(selected_headers)
                message["headers"].append((b"x-request-id", trace_id.encode("ascii")))  # token-only → safe
            await send(message)

        await self.app(scope, receive, send_with_id)
