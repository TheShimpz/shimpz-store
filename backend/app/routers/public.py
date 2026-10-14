"""Unauthenticated Store health and Assistant release metadata."""

import asyncio
import hashlib
import json
import threading
import time

from fastapi import APIRouter, Request
from fastapi.responses import Response

from app import catalog, config
from app.concurrency import run_bounded
from app.control import EXECUTOR as CONTROL_EXECUTOR
from app.protocol.http.v1 import payload as team_contract
from app.upstream import VERIFY_TIMEOUT_SECONDS, call, call_asset_bounded

router = APIRouter()


@router.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _catalog_locale(request: Request) -> str | None:
    """Admit exactly one closed `locale` query parameter and nothing else."""
    query = request.url.query
    return team_contract.canonical_locale(query.removeprefix("locale=")) if query.startswith("locale=") else None


def _catalog_body(locale: str) -> bytes | None:
    """Read, validate, project, and serialize one locale's catalog inside one control worker."""
    if not _catalog_loads.acquire(timeout=VERIFY_TIMEOUT_SECONDS):
        return None
    try:
        status, value = call(
            config.DEVELOPERS_URL,
            "GET",
            f"/api/v1/assistants?locale={locale}",
            timeout=VERIFY_TIMEOUT_SECONDS,
        )
    finally:
        _catalog_loads.release()
    if status != 200:
        return None
    try:
        projected = catalog.project_catalog(value, locale)
    except catalog.CatalogError:
        return None
    # UTF-8, not ASCII escapes: escaping multibyte text would inflate a full catalog past its consumers' limit.
    return json.dumps(projected, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode()


# One locale's served catalog is kept as long as its response says caches may keep it, and only one read of a locale
# runs at a time: every visitor arriving meanwhile shares it, so a burst of visitors costs Developers one catalog load,
# which it admits only two of at once. A failed read is never kept.
CATALOG_CACHE_SECONDS = 60
# Developers loads at most two catalogs at once and refuses a third, so reads of different locales queue here instead.
DEVELOPERS_CATALOG_LOADS = 2
_catalog_loads = threading.BoundedSemaphore(DEVELOPERS_CATALOG_LOADS)
_catalogs: dict[str, tuple[float, bytes]] = {}
_reading: dict[str, asyncio.Task[bytes | None]] = {}


async def _served_catalog(locale: str) -> tuple[float, bytes] | None:
    """One locale's catalog and when it was read, kept or read now; None when it is unavailable."""
    kept = _catalogs.get(locale)
    if kept is not None and time.monotonic() - kept[0] < CATALOG_CACHE_SECONDS:
        return kept
    reading = _reading.get(locale)
    if reading is None:
        reading = asyncio.create_task(_read_catalog(locale))
        _reading[locale] = reading
    # A visitor who leaves never cancels the read the others wait on.
    return await asyncio.shield(reading)


async def _read_catalog(locale: str) -> tuple[float, bytes] | None:
    try:
        body = await run_bounded(CONTROL_EXECUTOR, _catalog_body, locale)
        if body is None:
            return None
        _catalogs[locale] = (time.monotonic(), body)
        return _catalogs[locale]
    finally:
        del _reading[locale]


@router.get("/api/assistants")
async def assistant_catalog(request: Request) -> Response:
    # The visitor's interface language selects the catalog; caches key it by this exact URL.
    locale = _catalog_locale(request)
    if locale is None:
        return Response(
            content='{"detail":"Assistant catalog locale is invalid"}',
            status_code=400,
            media_type="application/json",
            headers={"Cache-Control": "no-store"},
        )
    served = await _served_catalog(locale)
    if served is None:
        return Response(
            content='{"detail":"Assistant catalog is unavailable"}',
            status_code=503,
            media_type="application/json",
            headers={"Cache-Control": "no-store"},
        )
    read_at, body = served
    # A kept catalog says how old it already is, so no cache after this one keeps it past its own lifetime.
    return Response(
        content=body,
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=60, s-maxage=300", "Age": str(int(time.monotonic() - read_at))},
    )


@router.get("/api/assistant-icons/{source_hash}/{icon_hash}.png")
async def assistant_icon(source_hash: str, icon_hash: str) -> Response:
    if team_contract.SHA256_RE.fullmatch(source_hash) is None or team_contract.SHA256_RE.fullmatch(icon_hash) is None:
        return _icon_unavailable()
    status, contents = await call_asset_bounded(
        CONTROL_EXECUTOR,
        config.DEVELOPERS_URL,
        f"/api/v1/assistant-publications/sha256:{source_hash}/icon.png",
        timeout=VERIFY_TIMEOUT_SECONDS,
    )
    if status != 200 or hashlib.sha256(contents).hexdigest() != icon_hash:
        return _icon_unavailable()
    return Response(
        content=contents,
        media_type="image/png",
        headers={
            "Cache-Control": config.IMMUTABLE_CACHE_CONTROL,
            "X-Content-Type-Options": "nosniff",
        },
    )


def _icon_unavailable() -> Response:
    return Response(
        content='{"detail":"Assistant icon is unavailable"}',
        status_code=503,
        media_type="application/json",
        headers={"Cache-Control": "no-store"},
    )
