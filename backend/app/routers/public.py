"""Unauthenticated Store health and Assistant release metadata."""

import asyncio
import contextlib
import hashlib
import json
import time
import weakref
from collections import OrderedDict
from collections.abc import AsyncIterator, Awaitable, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from app import catalog, config
from app.concurrency import BoundedThreadPoolExecutor, run_bounded
from app.config import CONTROL_QUEUE_MAX, CONTROL_WORKER_THREADS
from app.protocol.http.v1 import payload as team_contract
from app.upstream import call, call_asset

router = APIRouter()
# The bounded admission catalog and icon reads share; OAuth runs on its own executor.
CONTROL_EXECUTOR = BoundedThreadPoolExecutor(
    max_workers=CONTROL_WORKER_THREADS,
    max_outstanding=CONTROL_WORKER_THREADS + CONTROL_QUEUE_MAX,
    thread_name_prefix="shimpz-control",
)


@router.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _catalog_locale(request: Request) -> str | None:
    """Admit exactly one closed `locale` query parameter and nothing else."""
    query = request.url.query
    return team_contract.canonical_locale(query.removeprefix("locale=")) if query.startswith("locale=") else None


def _catalog_body(locale: str) -> bytes | None:
    """Read, validate, project, and serialize one locale's catalog inside one control worker."""
    status, value = call(f"/api/v1/assistants?locale={locale}")
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
_catalogs: dict[str, tuple[float, bytes]] = {}
_reading: dict[str, asyncio.Task[tuple[float, bytes] | None]] = {}


async def _served_catalog(locale: str) -> tuple[float, bytes] | None:
    """One locale's catalog and when it was read, kept or read now; None when it is unavailable."""
    kept = _catalogs.get(locale)
    if kept is not None and time.monotonic() - kept[0] < CATALOG_CACHE_SECONDS:
        return kept
    return await _shared(_reading, locale, lambda: _read_catalog(locale), limit=len(team_contract.CHAT_LOCALES))


async def _read_catalog(locale: str) -> tuple[float, bytes] | None:
    async with _developers_slot("catalog", DEVELOPERS_CATALOG_LOADS) as admitted:
        body = await run_bounded(CONTROL_EXECUTOR, _catalog_body, locale) if admitted else None
    if body is None:
        return None
    _catalogs[locale] = (time.monotonic(), body)
    return _catalogs[locale]


# Developers' few load slots are taken here, on the event loop, before any work reaches the control executor: a burst
# of reads waits for them without filling the executor catalog and icon reads share. The table belongs to the
# event loop serving the Store and starts again on another one.
_slots: dict[str, asyncio.Semaphore] = {}
_slots_loop: weakref.ReferenceType[asyncio.AbstractEventLoop] | None = None


@contextlib.asynccontextmanager
async def _developers_slot(kind: str, size: int) -> AsyncIterator[bool]:
    """Hold one of `size` Developers load slots of `kind`; False when none freed before the read's deadline."""
    global _slots_loop
    loop = asyncio.get_running_loop()
    if _slots_loop is None or _slots_loop() is not loop:
        _slots.clear()
        _slots_loop = weakref.ref(loop)
    slot = _slots.setdefault(kind, asyncio.Semaphore(size))
    try:
        await asyncio.wait_for(slot.acquire(), config.DEVELOPERS_TIMEOUT_SECONDS)
    except TimeoutError:
        yield False
        return
    try:
        yield True
    finally:
        slot.release()


async def _shared[K, T](
    reads: dict[K, asyncio.Task[T | None]], key: K, read: Callable[[], Awaitable[T | None]], *, limit: int
) -> T | None:
    """One read per key at a time: every request arriving while it runs awaits the same one.

    A request that leaves never cancels the read the others wait on, and the read leaves the table once it ends. At most
    `limit` keys are read at once: a request for another key past it is refused (None) instead of queued.
    """
    task = reads.get(key)
    if task is None:
        if len(reads) >= limit:
            return None
        task = asyncio.create_task(read())
        reads[key] = task
        task.add_done_callback(lambda _done: reads.pop(key, None))
    return await asyncio.shield(task)


def _uncached_error(detail: str, status: int) -> Response:
    """A closed JSON error no cache may keep."""
    return JSONResponse({"detail": detail}, status_code=status, headers={"Cache-Control": "no-store"})


@router.get("/api/assistants")
async def assistant_catalog(request: Request) -> Response:
    # The visitor's interface language selects the catalog; caches key it by this exact URL.
    locale = _catalog_locale(request)
    if locale is None:
        return _uncached_error("Assistant catalog locale is invalid", 400)
    served = await _served_catalog(locale)
    if served is None:
        return _uncached_error("Assistant catalog is unavailable", 503)
    read_at, body = served
    # A kept catalog says how old it already is, so no cache after this one keeps it past its own lifetime.
    return Response(
        content=body,
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=60, s-maxage=300", "Age": str(int(time.monotonic() - read_at))},
    )


# Developers verifies a publication's whole archive to answer one icon and admits only a few at once, while a catalog
# page asks for every icon together: the Store reads at most two at a time, so the rest wait instead of failing, and
# keeps each verified icon, which its hash names, within a count and a byte budget.
DEVELOPERS_ICON_LOADS = 2
MAX_KEPT_ICONS = 256
MAX_KEPT_ICON_BYTES = 8 * 1024 * 1024
# Distinct icons read or waiting for a load slot at once; a request for one more is refused, never queued without bound.
MAX_PENDING_ICON_READS = 64
_icons: OrderedDict[tuple[str, str], bytes] = OrderedDict()
_icon_reads: dict[tuple[str, str], asyncio.Task[bytes | None]] = {}


def _icon_body(source_hash: str, icon_hash: str) -> bytes | None:
    """Read one publication's icon inside one control worker; only bytes matching its hash are returned."""
    status, contents = call_asset(f"/api/v1/assistant-publications/sha256:{source_hash}/icon.png")
    if status != 200 or hashlib.sha256(contents).hexdigest() != icon_hash:
        return None
    return contents


def _keep_icon(key: tuple[str, str], contents: bytes) -> None:
    _icons[key] = contents
    _icons.move_to_end(key)
    while len(_icons) > MAX_KEPT_ICONS or sum(map(len, _icons.values())) > MAX_KEPT_ICON_BYTES:
        _icons.popitem(last=False)


async def _read_icon(key: tuple[str, str]) -> bytes | None:
    async with _developers_slot("icon", DEVELOPERS_ICON_LOADS) as admitted:
        contents = await run_bounded(CONTROL_EXECUTOR, _icon_body, *key) if admitted else None
    if contents is not None:
        _keep_icon(key, contents)
    return contents


@router.get("/api/assistant-icons/{source_hash}/{icon_hash}.png")
async def assistant_icon(source_hash: str, icon_hash: str) -> Response:
    if team_contract.SHA256_RE.fullmatch(source_hash) is None or team_contract.SHA256_RE.fullmatch(icon_hash) is None:
        return _icon_unavailable()
    key = (source_hash, icon_hash)
    contents = _icons.get(key)
    if contents is not None:
        _icons.move_to_end(key)
    else:
        contents = await _shared(_icon_reads, key, lambda: _read_icon(key), limit=MAX_PENDING_ICON_READS)
        if contents is None:
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
    return _uncached_error("Assistant icon is unavailable", 503)
