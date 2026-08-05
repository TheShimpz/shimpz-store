"""Unauthenticated Store health and Assistant release metadata."""

from __future__ import annotations

import hashlib
import json
import re

from fastapi import APIRouter
from fastapi.responses import Response

from app import catalog, config
from app.control import EXECUTOR as CONTROL_EXECUTOR
from app.upstream import VERIFY_TIMEOUT_SECONDS, call_asset_bounded, call_bounded

router = APIRouter()
_HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")


@router.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/assistants")
async def assistant_catalog() -> Response:
    status, value = await call_bounded(
        CONTROL_EXECUTOR,
        config.DEVELOPERS_URL,
        "GET",
        "/api/v1/assistants",
        timeout=VERIFY_TIMEOUT_SECONDS,
    )
    if status != 200:
        return Response(
            content='{"detail":"Assistant catalog is unavailable"}',
            status_code=503,
            media_type="application/json",
            headers={"Cache-Control": "no-store"},
        )
    try:
        projected = catalog.project_catalog(value)
    except catalog.CatalogError:
        return Response(
            content='{"detail":"Assistant catalog is unavailable"}',
            status_code=503,
            media_type="application/json",
            headers={"Cache-Control": "no-store"},
        )
    return Response(
        content=json.dumps(projected, separators=(",", ":"), sort_keys=True),
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=60, s-maxage=300"},
    )


@router.get("/api/assistant-icons/{source_hash}/{icon_hash}.png")
async def assistant_icon(source_hash: str, icon_hash: str) -> Response:
    if _HEX_DIGEST.fullmatch(source_hash) is None or _HEX_DIGEST.fullmatch(icon_hash) is None:
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
