"""Bounded one-hop JSON transport to trusted internal services."""

from __future__ import annotations

import functools
import http.client
import json
from urllib.parse import quote, urlparse

import structlog

from app.concurrency import BoundedThreadPoolExecutor, run_bounded

log = structlog.get_logger()

VERIFY_TIMEOUT_SECONDS = 5
CONTROL_PLANE_TIMEOUT_SECONDS = 30
CHAT_STOP_TIMEOUT_SECONDS = 10
FILE_NAME_HEADER = "X-Shimpz-Filename"


def _request(
    base: str,
    method: str,
    path: str,
    body: str | bytes | None,
    headers: dict[str, str],
    *,
    timeout: float,
) -> tuple[int, dict]:
    parsed = urlparse(base)
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=timeout)
    try:
        connection.request(method, path, body, headers)
        response = connection.getresponse()
        raw = response.read()
        return response.status, (json.loads(raw) if raw else {})
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("proxy_unreachable", base=base, path=path, error=str(exc))
        return 502, {"detail": "the Space is unreachable"}
    finally:
        connection.close()


def call(
    base: str,
    method: str,
    path: str,
    payload: dict | None = None,
    extra: dict | None = None,
    *,
    timeout: float,
) -> tuple[int, dict]:
    """Proxy one trusted internal hop with a closed generic failure."""
    headers: dict[str, str] = dict(extra or {})
    body = None
    if payload is not None:
        body = json.dumps(payload)
        headers["Content-Type"] = "application/json"
    return _request(base, method, path, body, headers, timeout=timeout)


def call_raw(
    base: str,
    path: str,
    body: bytes,
    *,
    filename: str,
    media_type: str,
    extra: dict | None = None,
    timeout: float,
) -> tuple[int, dict]:
    """Proxy one raw file body while retaining a JSON response contract."""
    headers: dict[str, str] = dict(extra or {})
    headers["Content-Type"] = media_type
    headers[FILE_NAME_HEADER] = quote(filename, safe="")
    return _request(base, "POST", path, body, headers, timeout=timeout)


async def call_bounded(
    executor: BoundedThreadPoolExecutor,
    *args,
    **kwargs,
) -> tuple[int, dict]:
    """Run one internal JSON hop through the caller's bounded executor."""
    return await run_bounded(executor, functools.partial(call, *args, **kwargs))


async def call_raw_bounded(
    executor: BoundedThreadPoolExecutor,
    *args,
    **kwargs,
) -> tuple[int, dict]:
    """Run one raw internal file hop through the caller's bounded executor."""
    return await run_bounded(executor, functools.partial(call_raw, *args, **kwargs))
