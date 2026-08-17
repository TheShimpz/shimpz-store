"""Prerendered SvelteKit files registered after every API and WebSocket route."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, PlainTextResponse, Response

from app.config import BUILD, HTML_CACHE_CONTROL, IMMUTABLE_CACHE_CONTROL

router = APIRouter()


def resolve(rel: str) -> Path | None:
    rel = rel.strip("/")
    if ".." in rel.split("/"):
        return None
    for candidate in (BUILD / rel, BUILD / f"{rel}.html", BUILD / rel / "index.html"):
        if candidate.is_file():
            return candidate
    return None


def cache_control(path: str, hit: Path) -> str:
    """Revalidate navigations while retaining SvelteKit's content-addressed asset cache."""
    rel = path.strip("/")
    if hit.suffix.lower() not in {".html", ".htm"} and rel.startswith("_app/immutable/"):
        return IMMUTABLE_CACHE_CONTROL
    return HTML_CACHE_CONTROL


def is_not_found_document(hit: Path) -> bool:
    try:
        relative = hit.relative_to(BUILD)
    except ValueError:
        return False
    return len(relative.parts) == 2 and relative.name == "404.html"


def not_found_document(path: str) -> Path | None:
    first_segment = path.strip("/").partition("/")[0]
    localized = resolve(f"{first_segment}/404")
    if localized is not None and is_not_found_document(localized):
        return localized
    fallback = resolve("en/404")
    return fallback if fallback is not None and is_not_found_document(fallback) else None


def html_navigation(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "").lower()


@router.get("/{path:path}")
def static_files(path: str, request: Request) -> Response:
    hit = resolve(path)
    if hit and not is_not_found_document(hit):
        return FileResponse(hit, headers={"Cache-Control": cache_control(path, hit)})
    if html_navigation(request):
        document = hit if hit and is_not_found_document(hit) else not_found_document(path)
        if document is not None:
            return FileResponse(
                document,
                status_code=404,
                headers={"Cache-Control": HTML_CACHE_CONTROL},
            )
    return PlainTextResponse(
        "not found",
        status_code=404,
        headers={"Cache-Control": HTML_CACHE_CONTROL},
    )
