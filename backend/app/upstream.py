"""Bounded one-hop JSON and asset transport to trusted internal services."""

import functools
import http.client
import json
from urllib.parse import urlparse

import structlog

from app.concurrency import BoundedThreadPoolExecutor, run_bounded

log = structlog.get_logger()

VERIFY_TIMEOUT_SECONDS = 5
MAX_JSON_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_ASSET_RESPONSE_BYTES = 1024 * 1024


def call(
    base: str, method: str, path: str, *, timeout: float, max_response_bytes: int = MAX_JSON_RESPONSE_BYTES
) -> tuple[int, dict]:
    """Proxy one bodiless trusted internal hop with a closed generic failure."""
    parsed = urlparse(base)
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=timeout)
    try:
        connection.request(method, path)
        response = connection.getresponse()
        raw = response.read(max_response_bytes + 1)
        if len(raw) > max_response_bytes:
            return 502, {"detail": "the upstream returned an oversized response"}
        return response.status, (json.loads(raw) if raw else {})
    except (OSError, UnicodeError, json.JSONDecodeError, http.client.HTTPException) as exc:
        log.warning("proxy_unreachable", base=base, path=path, error=str(exc))
        return 502, {"detail": "the upstream is unreachable"}
    finally:
        connection.close()


def call_asset(base: str, path: str, *, timeout: float) -> tuple[int, bytes]:
    """Read one bounded immutable asset from a fixed trusted internal service."""
    parsed = urlparse(base)
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=timeout)
    try:
        connection.request("GET", path, headers={"Accept": "image/png"})
        response = connection.getresponse()
        if response.status != 200:
            response.read(MAX_ASSET_RESPONSE_BYTES + 1)
            return response.status, b""
        media_type = (response.getheader("Content-Type") or "").partition(";")[0].strip().lower()
        length = response.getheader("Content-Length")
        if media_type != "image/png" or length is None:
            return 502, b""
        try:
            expected = int(length)
        except ValueError:
            return 502, b""
        if not 1 <= expected <= MAX_ASSET_RESPONSE_BYTES:
            return 502, b""
        contents = response.read(MAX_ASSET_RESPONSE_BYTES + 1)
        return (200, contents) if len(contents) == expected else (502, b"")
    except (OSError, UnicodeError, http.client.HTTPException) as exc:
        log.warning("asset_proxy_unreachable", base=base, path=path, error=str(exc))
        return 502, b""
    finally:
        connection.close()


async def call_asset_bounded(
    executor: BoundedThreadPoolExecutor,
    *args,
    **kwargs,
) -> tuple[int, bytes]:
    """Run one internal asset read through the caller's bounded executor."""
    return await run_bounded(executor, functools.partial(call_asset, *args, **kwargs))
