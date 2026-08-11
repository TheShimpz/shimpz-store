"""Bounded one-hop JSON transport to trusted internal services."""

from __future__ import annotations

import functools
import http.client
import json
from typing import NamedTuple, NotRequired, TypedDict, Unpack
from urllib.parse import quote, urlparse

import structlog

from app.concurrency import BoundedThreadPoolExecutor, run_bounded

log = structlog.get_logger()

VERIFY_TIMEOUT_SECONDS = 5
CONTROL_PLANE_TIMEOUT_SECONDS = 30
CHAT_STOP_TIMEOUT_SECONDS = 10
FILE_NAME_HEADER = "X-Shimpz-Filename"
MAX_JSON_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_ASSET_RESPONSE_BYTES = 1024 * 1024


class _Request(NamedTuple):
    base: str
    method: str
    path: str
    body: str | bytes | None
    headers: dict[str, str]
    timeout: float
    max_response_bytes: int


class _CallOptions(TypedDict):
    timeout: float
    max_response_bytes: NotRequired[int]


class _RawCallOptions(TypedDict):
    filename: str
    media_type: str
    extra: NotRequired[dict[str, str] | None]
    timeout: float


def _request(request: _Request) -> tuple[int, dict]:
    parsed = urlparse(request.base)
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=request.timeout)
    try:
        connection.request(request.method, request.path, request.body, request.headers)
        response = connection.getresponse()
        raw = response.read(request.max_response_bytes + 1)
        if len(raw) > request.max_response_bytes:
            return 502, {"detail": "the Space returned an oversized response"}
        return response.status, (json.loads(raw) if raw else {})
    except (OSError, UnicodeError, json.JSONDecodeError, http.client.HTTPException) as exc:
        log.warning("proxy_unreachable", base=request.base, path=request.path, error=str(exc))
        return 502, {"detail": "the Space is unreachable"}
    finally:
        connection.close()


def call(
    base: str,
    method: str,
    path: str,
    payload: dict | None = None,
    extra: dict[str, str] | None = None,
    **options: Unpack[_CallOptions],
) -> tuple[int, dict]:
    """Proxy one trusted internal hop with a closed generic failure."""
    headers: dict[str, str] = dict(extra or {})
    body = None
    if payload is not None:
        body = json.dumps(payload)
        headers["Content-Type"] = "application/json"
    return _request(
        _Request(
            base,
            method,
            path,
            body,
            headers,
            options["timeout"],
            options.get("max_response_bytes", MAX_JSON_RESPONSE_BYTES),
        )
    )


def call_raw(
    base: str,
    path: str,
    body: bytes,
    **options: Unpack[_RawCallOptions],
) -> tuple[int, dict]:
    """Proxy one raw file body while retaining a JSON response contract."""
    headers: dict[str, str] = dict(options.get("extra") or {})
    headers["Content-Type"] = options["media_type"]
    headers[FILE_NAME_HEADER] = quote(options["filename"], safe="")
    return _request(
        _Request(base, "POST", path, body, headers, options["timeout"], MAX_JSON_RESPONSE_BYTES)
    )


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
