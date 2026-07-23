"""Unauthenticated Store health and Assistant release metadata."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.assistant_releases import (
    ASSISTANT_RELEASE_CACHE_CONTROL,
    ASSISTANT_RELEASE_FEED_BODY,
    ASSISTANT_RELEASE_FEED_ETAG,
    if_none_match_matches,
)

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
