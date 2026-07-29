"""Unauthenticated Store health and Assistant release metadata."""

from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import Response

from app import catalog, config
from app.assistant_releases import (
    ASSISTANT_RELEASE_CACHE_CONTROL,
    ASSISTANT_RELEASE_FEED_BODY,
    ASSISTANT_RELEASE_FEED_ETAG,
    if_none_match_matches,
)
from app.control import EXECUTOR as CONTROL_EXECUTOR
from app.upstream import VERIFY_TIMEOUT_SECONDS, call_bounded

router = APIRouter()


@router.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/releases/assistants")
def assistant_release_feed(request: Request) -> Response:
    """Serve cacheable notification metadata without granting installation authority."""
    headers = {
        "Cache-Control": ASSISTANT_RELEASE_CACHE_CONTROL,
        "ETag": ASSISTANT_RELEASE_FEED_ETAG,
    }
    if if_none_match_matches(request.headers.get("if-none-match"), ASSISTANT_RELEASE_FEED_ETAG):
        return Response(status_code=304, headers=headers)
    return Response(
        content=ASSISTANT_RELEASE_FEED_BODY,
        media_type="application/json",
        headers=headers,
    )


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
