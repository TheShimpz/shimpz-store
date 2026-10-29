"""Bind a request trace ID into structlog context variables.

Every log line for the request carries the ID across nested calls. The middleware reuses an inbound
X-Request-ID propagated by a caller or mints one, then echoes it so a browser or calling service can
follow the same request end-to-end.

The inbound header is ATTACKER-CONTROLLED, so it is never trusted raw: it flows into a response header (a
control byte would crash the ASGI send / enable header injection) and into contextvars + every log line (an
oversized value would bloat them). _clean() decodes safely (latin-1 never raises on bad bytes), keeps only a
conservative token charset, and caps the length — an empty/oversized/hostile ID is replaced with a fresh one.

The middleware is also the only author of the browser security headers. Its script policy admits this origin and the
exact inline scripts each prerendered page's own build policy admits, by hash, never 'unsafe-inline'; the OAuth
completion page alone keeps the nonce policy its route sets.
"""

import re
from pathlib import Path
from uuid import uuid4

import structlog

from app.config import BUILD

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")
_CSP_PREFIX = b"default-src 'self'; base-uri 'self'; object-src 'none'; "
# Every DOM HTML or script-URL sink refuses a plain string; only Svelte's own template policy may create the trusted
# values it needs, so any other injection sink, in this application or a dependency, fails closed at runtime.
_CSP_TRUSTED_TYPES = b"require-trusted-types-for 'script'; trusted-types svelte-trusted-html; "
_CSP_STYLE_AND_REST = (
    b"style-src 'self' 'unsafe-inline'; "
    b"img-src 'self'; font-src 'self' data:; connect-src 'self'; "
    b"frame-src 'none'; "
    b"worker-src 'self' blob:; manifest-src 'self'; upgrade-insecure-requests"
)
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
}


_META_PREFIX = '<meta http-equiv="content-security-policy" content="'
_PAGE_TRUSTED_TYPES = "require-trusted-types-for 'script'; trusted-types svelte-trusted-html"
_SHA256_SOURCE = re.compile(r"'sha256-[A-Za-z0-9+/]{43}='")


class BuildPolicyError(ValueError):
    """A prerendered page has no build policy, several, or one outside the exact grammar the build writes."""


def _page_sources(document: str) -> list[str]:
    """The hash sources of the one policy the build wrote into a page, which may name none."""
    policies = document.split(_META_PREFIX)[1:]
    if len(policies) != 1:
        raise BuildPolicyError("page script policy is invalid")
    policy, closed, _rest = policies[0].partition('"')
    scripts = policy.removesuffix("; " + _PAGE_TRUSTED_TYPES)
    tokens = scripts.split(" ")
    if (
        not closed
        or scripts == policy
        or tokens[:2] != ["script-src", "'self'"]
        or not all(_SHA256_SOURCE.fullmatch(token) for token in tokens[2:])
    ):
        raise BuildPolicyError("page script policy is invalid")
    return tokens[2:]


def build_script_sources(build: Path) -> tuple[bytes, ...]:
    """The hash source of every inline script the prerendered pages' own policies admit, in one stable order.

    SvelteKit hashes each page's inline scripts into one meta policy of that page (`kit.csp` in hash mode). Only the
    immutable build the image ships is read, never a response body, so no reflected script can ever be admitted; a page
    without exactly one policy of the build's grammar refuses the whole build, and no build admits this origin only.
    """
    sources = set()
    for document in sorted(build.rglob("*.html")):
        sources.update(_page_sources(document.read_text(encoding="utf-8")))
    return tuple(sorted(source.encode("ascii") for source in sources))


def page_headers(build: Path) -> tuple[tuple[bytes, bytes], ...]:
    """The page header set: one script policy bound to the build's exact inline scripts."""
    script_policy = b"script-src " + b" ".join((b"'self'", *build_script_sources(build))) + b"; "
    return (
        _COMMON_SECURITY_HEADERS[0],
        (
            b"content-security-policy",
            _CSP_PREFIX
            + b"frame-ancestors 'none'; form-action 'self'; "
            + script_policy
            + _CSP_TRUSTED_TYPES
            + _CSP_STYLE_AND_REST,
        ),
        _COMMON_SECURITY_HEADERS[1],
        (b"x-frame-options", b"DENY"),
        _COMMON_SECURITY_HEADERS[2],
        _COMMON_SECURITY_HEADERS[3],
    )


_NO_REFERRER_PATHS = frozenset(
    {
        "/api/oauth/cloudflare/start",
        "/api/oauth/cloudflare/callback",
    }
)
_RESPONSE_CSP_PATHS = frozenset({"/api/oauth/cloudflare/callback"})


# The shipped build is immutable, so its policy is computed while the app loads rather than inside a first request.
_PAGE_HEADERS = page_headers(BUILD)


def _path_headers(path: str) -> tuple[tuple[bytes, bytes], ...]:
    headers = _PAGE_HEADERS
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
        path_headers = _path_headers(scope.get("path", ""))

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                response_headers = message.get("headers") or []
                response_csp = next(
                    (value for name, value in response_headers if name.lower() == b"content-security-policy"),
                    None,
                )
                selected_headers = path_headers
                if scope.get("path", "") in _RESPONSE_CSP_PATHS and response_csp is not None:
                    selected_headers = tuple(
                        (name, response_csp) if name == b"content-security-policy" else (name, value)
                        for name, value in path_headers
                    )
                managed = _MANAGED_SECURITY_HEADERS | {b"x-request-id"}
                message["headers"] = [(name, value) for name, value in response_headers if name.lower() not in managed]
                message["headers"].extend(selected_headers)
                message["headers"].append((b"x-request-id", trace_id.encode("ascii")))  # token-only → safe
            await send(message)

        await self.app(scope, receive, send_with_id)
