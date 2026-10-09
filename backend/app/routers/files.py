"""Opaque Team file routes."""

import asyncio
import threading
from collections.abc import AsyncIterator
from contextlib import aclosing

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from python_multipart.exceptions import FormParserError
from starlette.datastructures import FormData, UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser

from app import config
from app.access import mutation_origin_allowed, private_json, require_session, require_team_id
from app.control import EXECUTOR as CONTROL_EXECUTOR
from app.payloads import ClientPayloadError
from app.projections import public_file_deletion, public_file_inventory, public_file_upload
from app.protocol.http.v1 import payload as team_contract
from app.upstream import CONTROL_PLANE_TIMEOUT_SECONDS, call_bounded, call_raw_bounded

log = structlog.get_logger()
router = APIRouter()

MAX_UPLOAD_BYTES = team_contract.MAX_FILE_UPLOAD_BYTES
# Multipart framing (boundary lines and one part's headers) admitted beyond the file bytes themselves.
MULTIPART_OVERHEAD_BYTES = 64 * 1024
ONE_FILE = {"detail": "expected exactly one multipart file named file"}
# Uploads buffered in memory at once, each held from parsing through the Team hop. An upload can briefly hold its
# parsed part and its forwarded copy, so this keeps upload memory well inside the Store's container limit.
UPLOAD_CONCURRENCY = 4
UPLOAD_ADMISSION = threading.BoundedSemaphore(UPLOAD_CONCURRENCY)
# Absolute bound on receiving one upload body (a full file at about 2 Mbit/s), so a stalled client cannot hold its
# admission slot and partial buffer indefinitely.
UPLOAD_READ_DEADLINE_SECONDS = 120


class UploadTooLargeError(Exception):
    """The request body passed its byte bound while it was being read."""


class _InMemoryMultiPartParser(MultiPartParser):
    """Parse one upload in memory and record whether its closing boundary arrived.

    Memory keeps a Team upload off the Store's small /tmp; the underlying parser never verifies the closing boundary.
    """

    spool_max_size = MAX_UPLOAD_BYTES + MULTIPART_OVERHEAD_BYTES
    ended = False

    def on_end(self) -> None:
        self.ended = True

    def close_files(self) -> None:
        """Release the partially buffered parts of an abandoned parse."""
        for file in self._files_to_close_on_error:
            file.close()


async def bounded_stream(stream: AsyncIterator[bytes], limit: int) -> AsyncIterator[bytes]:
    """Yield the body until it passes ``limit`` bytes, then stop reading it."""
    received = 0
    async for chunk in stream:
        received += len(chunk)
        if received > limit:
            raise UploadTooLargeError
        yield chunk


def _too_large() -> JSONResponse:
    return private_json({"detail": f"file too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)"}, 413)


@router.get("/api/teams/{team_id}/files")
async def team_files(request: Request, team_id: str) -> JSONResponse:
    """List opaque file metadata; file bytes and host paths remain controller-private."""
    token, _ = await require_session(request)
    team_id = require_team_id(team_id)
    status, body = await call_bounded(
        CONTROL_EXECUTOR,
        config.TEAM_URL,
        "GET",
        f"/v1/teams/{team_id}/files",
        extra={team_contract.ACCOUNT_SESSION_HEADER: token},
        timeout=CONTROL_PLANE_TIMEOUT_SECONDS,
    )
    if status != 200:
        return private_json(body, status)
    inventory = public_file_inventory(body, team_id)
    if inventory is None:
        log.warning("team_file_inventory_invalid", team_id=team_id)
        return private_json({"detail": "invalid Team storage inventory"}, 502)
    return private_json(inventory)


async def _parse_upload(request: Request) -> tuple[FormData, bool] | JSONResponse:
    """Parse the multipart body within its byte bound and read deadline, reporting whether it was terminated."""
    async with aclosing(bounded_stream(request.stream(), MAX_UPLOAD_BYTES + MULTIPART_OVERHEAD_BYTES)) as body:
        parser = _InMemoryMultiPartParser(request.headers, body, max_files=1, max_fields=0)
        try:
            async with asyncio.timeout(UPLOAD_READ_DEADLINE_SECONDS):
                return await parser.parse(), parser.ended
        except TimeoutError:
            parser.close_files()
            return private_json({"detail": "upload was not received in time"}, 408)
        except UploadTooLargeError:
            return _too_large()
        except MultiPartException, FormParserError:
            return private_json(ONE_FILE, 400)


async def _read_one_file(request: Request) -> tuple[UploadFile, bytes] | JSONResponse:
    """Read the single file part of an admitted upload, bounded while streaming and kept in memory."""
    if not request.headers.get("content-type", "").lower().startswith("multipart/form-data"):
        return private_json(ONE_FILE, 400)
    parsed = await _parse_upload(request)
    if isinstance(parsed, JSONResponse):
        return parsed
    form, ended = parsed
    file = form.get("file")
    if not ended or list(form.keys()) != ["file"] or not isinstance(file, UploadFile):
        return private_json(ONE_FILE, 400)
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        return _too_large()
    return file, data


@router.post("/api/teams/{team_id}/files")
async def team_file_upload(request: Request, team_id: str) -> JSONResponse:
    """Upload one opaque Team object without granting a Brain or Assistant filesystem access.

    The body is read only after the account and origin are admitted and an upload slot is free, and only up to the
    file limit plus multipart framing; it must hold exactly one file part named ``file`` and nothing else.
    """
    token, account_id = await require_session(request)
    if not mutation_origin_allowed(request.headers.get("origin")):
        raise ClientPayloadError(403, "forbidden origin")
    team_id = require_team_id(team_id)
    if not UPLOAD_ADMISSION.acquire(blocking=False):
        log.warning("store_capacity_rejected", path=request.url.path)
        response = private_json({"detail": "Store upload capacity reached"}, 429)
        response.headers["Retry-After"] = "1"
        return response
    try:
        return await _forward_upload(request, team_id, token, account_id)
    finally:
        UPLOAD_ADMISSION.release()


async def _forward_upload(request: Request, team_id: str, token: str, account_id: str) -> JSONResponse:
    """Read one admitted upload and forward it to Team while the caller holds an upload admission slot."""
    read = await _read_one_file(request)
    if isinstance(read, JSONResponse):
        return read
    file, data = read
    filename = team_contract.canonical_filename(file.filename or "upload.bin")
    media_type = team_contract.canonical_media_type(file.content_type)
    if filename is None or media_type is None:
        return private_json({"detail": "invalid file metadata"}, 400)
    status, body = await call_raw_bounded(
        CONTROL_EXECUTOR,
        config.TEAM_URL,
        f"/v1/teams/{team_id}/files",
        data,
        filename=filename,
        media_type=media_type,
        extra={team_contract.ACCOUNT_SESSION_HEADER: token},
        timeout=CONTROL_PLANE_TIMEOUT_SECONDS,
    )
    log.info(
        "team_file_upload",
        account=account_id,
        team_id=team_id,
        bytes=len(data),
        status=status,
    )
    if status != 200:
        return private_json(body, status)
    uploaded = public_file_upload(body, team_id)
    if uploaded is None:
        log.warning("team_file_upload_invalid", team_id=team_id)
        return private_json({"detail": "invalid Team storage response"}, 502)
    return private_json(uploaded)


@router.delete("/api/teams/{team_id}/files/{file_id}")
async def team_file_delete(request: Request, team_id: str, file_id: str) -> JSONResponse:
    token, account_id = await require_session(request)
    if not mutation_origin_allowed(request.headers.get("origin")):
        raise ClientPayloadError(403, "forbidden origin")
    team_id = require_team_id(team_id)
    opaque_id = team_contract.canonical_file_id(file_id)
    if opaque_id is None:
        raise ClientPayloadError(404, "file not found")
    status, body = await call_bounded(
        CONTROL_EXECUTOR,
        config.TEAM_URL,
        "DELETE",
        f"/v1/teams/{team_id}/files/{opaque_id}",
        extra={team_contract.ACCOUNT_SESSION_HEADER: token},
        timeout=CONTROL_PLANE_TIMEOUT_SECONDS,
    )
    log.info(
        "team_file_delete",
        account=account_id,
        team_id=team_id,
        file_id=opaque_id,
        status=status,
    )
    if status != 200:
        return private_json(body, status)
    deleted = public_file_deletion(body, team_id, opaque_id)
    if deleted is None:
        log.warning("team_file_delete_invalid", team_id=team_id, file_id=opaque_id)
        return private_json({"detail": "invalid Team storage response"}, 502)
    return private_json(deleted)
