"""Unauthenticated Store health and Assistant release metadata."""

from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import Response

from app import catalog, config
from app.control import EXECUTOR as CONTROL_EXECUTOR
from app.upstream import VERIFY_TIMEOUT_SECONDS, call_bounded

router = APIRouter()


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
