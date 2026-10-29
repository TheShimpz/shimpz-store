"""Prerendered SvelteKit files registered after every API route."""

import os
from email.utils import formatdate
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse, Response
from starlette.types import Receive, Scope, Send

from app.config import BUILD, HTML_CACHE_CONTROL, IMMUTABLE_CACHE_CONTROL

router = APIRouter()
ROOT_LOCATION = "/en"
# The exact Content-Type of every file kind the build ships, captured from the media types the Python runtime image
# served; any other suffix is opaque bytes. Suffixes compare in ASCII lower case.
MEDIA_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".txt": "text/plain; charset=utf-8",
    ".xml": "text/xml; charset=utf-8",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ico": "image/vnd.microsoft.icon",
    ".webmanifest": "application/manifest+json",
}
OPAQUE_MEDIA_TYPE = "application/octet-stream"
# IMF-fixdate names four-digit years only: 1970-01-01T00:00:00Z through 9999-12-31T23:59:59Z.
LAST_MODIFIED_SECONDS = range(253402300800)


def media_type(hit: Path) -> str:
    return MEDIA_TYPES.get(hit.suffix.lower(), OPAQUE_MEDIA_TYPE)


def entity_tag(mtime_ns: int, size: int) -> str:
    """The validator of one file version: its nanosecond mtime and its size, in lowercase sign-magnitude hex."""
    return f'"{mtime_ns:x}-{size:x}"'


def last_modified(mtime_ns: int) -> str | None:
    """The file's whole mtime second as an IMF-fixdate, or None outside the four-digit years the format names."""
    second = mtime_ns // 1_000_000_000
    return formatdate(second, usegmt=True) if second in LAST_MODIFIED_SECONDS else None


class WholeFileResponse(FileResponse):
    """One whole build file: no byte ranges, an integer validator, and the Store's closed media types."""

    def __init__(self, path: Path, *, status_code: int = 200, headers: dict[str, str]) -> None:
        super().__init__(path, status_code=status_code, headers=headers, media_type=media_type(path))
        del self.headers["accept-ranges"]

    def set_stat_headers(self, stat_result: os.stat_result) -> None:
        self.headers.setdefault("content-length", str(stat_result.st_size))
        modified = last_modified(stat_result.st_mtime_ns)
        if modified is not None:
            self.headers.setdefault("last-modified", modified)
        self.headers.setdefault("etag", entity_tag(stat_result.st_mtime_ns, stat_result.st_size))

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # A Range or If-Range header never selects part of a file: every answer is the whole file.
        headers = [(name, value) for name, value in scope["headers"] if name not in {b"range", b"if-range"}]
        await super().__call__({**scope, "headers": headers}, receive, send)


def root_redirect() -> RedirectResponse:
    """Send the site root to the default English locale; every locale's pages link each other from there."""
    return RedirectResponse(ROOT_LOCATION, status_code=308, headers={"Cache-Control": HTML_CACHE_CONTROL})


# GET and HEAD are two routes, GET first, so another method on the root answers the same `Allow: GET` as every other
# page instead of a header listing a set in hash order.
router.add_api_route("/", root_redirect, methods=["GET"])
router.add_api_route("/", root_redirect, methods=["HEAD"])


def resolve(rel: str) -> Path | None:
    """Map a request path to one regular file whose real path, symlinks resolved, stays inside BUILD.

    A path holding a NUL or any other C0 control names no file: no build file has one in its name.
    """
    if any(character < " " for character in rel):
        return None
    rel = rel.strip("/")
    if ".." in rel.split("/"):
        return None
    root = os.path.realpath(BUILD)
    for relative in (rel, f"{rel}.html", f"{rel}/index.html" if rel else "index.html"):
        candidate = os.path.realpath(Path(root, relative))
        if candidate.startswith(root + os.sep) and Path(candidate).is_file():
            return Path(candidate)
    return None


def cache_control(path: str, hit: Path) -> str:
    """Revalidate navigations while retaining SvelteKit's content-addressed asset cache."""
    rel = path.strip("/")
    if hit.suffix.lower() not in {".html", ".htm"} and rel.startswith("_app/immutable/"):
        return IMMUTABLE_CACHE_CONTROL
    return HTML_CACHE_CONTROL


def is_not_found_document(hit: Path) -> bool:
    try:
        relative = hit.relative_to(os.path.realpath(BUILD))
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
        return WholeFileResponse(hit, headers={"Cache-Control": cache_control(path, hit)})
    if html_navigation(request):
        document = hit if hit and is_not_found_document(hit) else not_found_document(path)
        if document is not None:
            return WholeFileResponse(
                document,
                status_code=404,
                headers={"Cache-Control": HTML_CACHE_CONTROL},
            )
    return PlainTextResponse(
        "not found",
        status_code=404,
        headers={"Cache-Control": HTML_CACHE_CONTROL},
    )
