"""Bounded one-hop JSON and asset transport to Developers."""

import http.client
import json
from urllib.parse import urlparse

import structlog

from app import config

log = structlog.get_logger()

MAX_JSON_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_ASSET_RESPONSE_BYTES = 1024 * 1024


def _connection() -> http.client.HTTPConnection:
    parsed = urlparse(config.DEVELOPERS_URL)
    return http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=config.DEVELOPERS_TIMEOUT_SECONDS)


def call(path: str) -> tuple[int, dict]:
    """Read one bounded JSON document from Developers with a closed generic failure."""
    connection = _connection()
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        raw = response.read(MAX_JSON_RESPONSE_BYTES + 1)
        if len(raw) > MAX_JSON_RESPONSE_BYTES:
            return 502, {"detail": "the upstream returned an oversized response"}
        return response.status, (json.loads(raw) if raw else {})
    except (OSError, UnicodeError, json.JSONDecodeError, http.client.HTTPException) as exc:
        log.warning("proxy_unreachable", path=path, error=str(exc))
        return 502, {"detail": "the upstream is unreachable"}
    finally:
        connection.close()


def call_asset(path: str) -> tuple[int, bytes]:
    """Read one bounded immutable asset from Developers."""
    connection = _connection()
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
        log.warning("asset_proxy_unreachable", path=path, error=str(exc))
        return 502, b""
    finally:
        connection.close()
