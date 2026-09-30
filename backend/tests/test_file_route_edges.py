"""Failure coverage for opaque Team file routes."""

from __future__ import annotations

import asyncio
import secrets
import threading

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app import authn
from app.main import app
from app.routers import files

FILE_ID = "a" * 32
ORIGIN = {"Origin": "https://shimpz.com"}


def _session(authenticated: bool = True):
    token = secrets.token_hex(16) if authenticated else ""

    async def current(_request):
        return token, "account" if token else "", "user" if token else ""

    return current


def test_file_routes_reject_unauthenticated_requests(monkeypatch):
    monkeypatch.setattr(authn, "authed_account_bounded", _session(False))
    with TestClient(app) as client:
        listing = client.get("/api/teams/team/files")
        upload = client.post(
            "/api/teams/team/files",
            files={"file": ("file.txt", b"data", "text/plain")},
            headers=ORIGIN,
        )
        deletion = client.delete(f"/api/teams/team/files/{FILE_ID}", headers=ORIGIN)
    assert [response.status_code for response in (listing, upload, deletion)] == [401, 401, 401]


def test_file_listing_rejects_bad_team_upstream_failure_and_invalid_projection(monkeypatch):
    monkeypatch.setattr(authn, "authed_account_bounded", _session())
    responses = iter(((503, {"detail": "unavailable"}), (200, {})))

    async def upstream(*_args, **_kwargs):
        return next(responses)

    monkeypatch.setattr(files, "call_bounded", upstream)
    with TestClient(app) as client:
        bad_team = client.get("/api/teams/Invalid/files")
        unavailable = client.get("/api/teams/team/files")
        invalid = client.get("/api/teams/team/files")
    assert bad_team.status_code == 400
    assert unavailable.status_code == 503
    assert invalid.status_code == 502


def test_file_upload_rejects_bad_team_size_and_metadata(monkeypatch):
    monkeypatch.setattr(authn, "authed_account_bounded", _session())
    with TestClient(app) as client:
        bad_team = client.post(
            "/api/teams/Invalid/files",
            files={"file": ("file.txt", b"data", "text/plain")},
            headers=ORIGIN,
        )
        monkeypatch.setattr(files, "MAX_UPLOAD_BYTES", 2)
        oversized = client.post(
            "/api/teams/team/files",
            files={"file": ("file.txt", b"abc", "text/plain")},
            headers=ORIGIN,
        )
        monkeypatch.setattr(files, "MULTIPART_OVERHEAD_BYTES", 0)
        streamed_oversize = client.post(
            "/api/teams/team/files",
            files={"file": ("file.txt", b"abc", "text/plain")},
            headers=ORIGIN,
        )
        monkeypatch.setattr(files, "MAX_UPLOAD_BYTES", files.team_contract.MAX_FILE_UPLOAD_BYTES)
        invalid = client.post(
            "/api/teams/team/files",
            files={"file": ("../file.txt", b"data", "text/plain")},
            headers=ORIGIN,
        )
    assert bad_team.status_code == 400
    assert oversized.status_code == 413
    assert streamed_oversize.status_code == 413
    assert invalid.status_code == 400


def test_file_upload_forwards_upstream_failure_and_rejects_invalid_projection(monkeypatch):
    monkeypatch.setattr(authn, "authed_account_bounded", _session())
    responses = iter(((503, {"detail": "unavailable"}), (200, {})))

    async def upstream(*_args, **_kwargs):
        return next(responses)

    monkeypatch.setattr(files, "call_raw_bounded", upstream)
    with TestClient(app) as client:
        unavailable = client.post(
            "/api/teams/team/files",
            files={"file": ("file.txt", b"data", "text/plain")},
            headers=ORIGIN,
        )
        invalid = client.post(
            "/api/teams/team/files",
            files={"file": ("file.txt", b"data", "text/plain")},
            headers=ORIGIN,
        )
    assert unavailable.status_code == 503
    assert invalid.status_code == 502


def test_file_deletion_rejects_origin_team_and_file_identity(monkeypatch):
    monkeypatch.setattr(authn, "authed_account_bounded", _session())
    with TestClient(app) as client:
        forbidden = client.delete(f"/api/teams/team/files/{FILE_ID}")
        bad_team = client.delete(f"/api/teams/Invalid/files/{FILE_ID}", headers=ORIGIN)
        bad_file = client.delete("/api/teams/team/files/not-an-id", headers=ORIGIN)
    assert forbidden.status_code == 403
    assert bad_team.status_code == 400
    assert bad_file.status_code == 404


def test_file_deletion_forwards_upstream_failure_and_rejects_invalid_projection(monkeypatch):
    monkeypatch.setattr(authn, "authed_account_bounded", _session())
    responses = iter(((503, {"detail": "unavailable"}), (200, {})))

    async def upstream(*_args, **_kwargs):
        return next(responses)

    monkeypatch.setattr(files, "call_bounded", upstream)
    with TestClient(app) as client:
        unavailable = client.delete(f"/api/teams/team/files/{FILE_ID}", headers=ORIGIN)
        invalid = client.delete(f"/api/teams/team/files/{FILE_ID}", headers=ORIGIN)
    assert unavailable.status_code == 503
    assert invalid.status_code == 502


def test_an_upload_is_refused_before_its_body_is_read(monkeypatch):
    """Authentication and origin admission run before any multipart body is read or spooled."""
    read = []
    original = Request.stream

    def recording(self):
        read.append(self.url.path)
        return original(self)

    monkeypatch.setattr(Request, "stream", recording)
    body = {"file": ("file.txt", b"data" * 1024, "text/plain")}
    with TestClient(app) as client:
        monkeypatch.setattr(authn, "authed_account_bounded", _session(False))
        anonymous = client.post("/api/teams/team/files", files=body, headers=ORIGIN)
        monkeypatch.setattr(authn, "authed_account_bounded", _session())
        foreign = client.post("/api/teams/team/files", files=body)
    assert (anonymous.status_code, foreign.status_code) == (401, 403)
    assert read == []


def test_an_upload_admits_exactly_one_file_part_and_no_fields(monkeypatch):
    monkeypatch.setattr(authn, "authed_account_bounded", _session())
    forwarded = []

    async def upstream(*args, **_kwargs):
        forwarded.append(args)
        return 200, {}

    monkeypatch.setattr(files, "call_raw_bounded", upstream)
    with TestClient(app) as client:
        two_files = client.post(
            "/api/teams/team/files",
            files=[("file", ("a.txt", b"a", "text/plain")), ("file", ("b.txt", b"b", "text/plain"))],
            headers=ORIGIN,
        )
        with_field = client.post(
            "/api/teams/team/files",
            files={"file": ("a.txt", b"a", "text/plain")},
            data={"note": "x"},
            headers=ORIGIN,
        )
        wrong_name = client.post(
            "/api/teams/team/files", files={"upload": ("a.txt", b"a", "text/plain")}, headers=ORIGIN
        )
        not_multipart = client.post("/api/teams/team/files", content=b"raw", headers=ORIGIN)
    assert [r.status_code for r in (two_files, with_field, wrong_name, not_multipart)] == [400, 400, 400, 400]
    assert forwarded == []


def test_the_upload_stream_stops_at_its_byte_bound_without_draining_the_body():
    pulled = []

    async def body():
        for index in range(100):
            pulled.append(index)
            yield b"x" * 1024

    async def drain():
        async for _chunk in files.bounded_stream(body(), 2048):
            pass

    with pytest.raises(files.UploadTooLargeError):
        asyncio.run(drain())
    assert pulled == [0, 1, 2]


def test_malformed_or_unterminated_multipart_is_refused_without_dispatch(monkeypatch):
    monkeypatch.setattr(authn, "authed_account_bounded", _session())
    forwarded = []

    async def upstream(*args, **_kwargs):
        forwarded.append(args)
        return 200, {}

    monkeypatch.setattr(files, "call_raw_bounded", upstream)
    boundary = "shimpzboundary"
    part = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="a.txt"\r\n'
        "Content-Type: text/plain\r\n\r\n"
        "data\r\n"
    )
    headers = {**ORIGIN, "Content-Type": f"multipart/form-data; boundary={boundary}"}
    bodies = {
        # A syntax error in the framing itself.
        "malformed": f"--{boundary}\r\nnot a header line\r\n\r\n",
        # A completed file part followed by an unfinished second part and no closing boundary.
        "unterminated": part + f"--{boundary}\r\nContent-Disposition: form-data; name=",
    }
    with TestClient(app, raise_server_exceptions=False) as client:
        statuses = {
            name: client.post("/api/teams/team/files", content=body, headers=headers).status_code
            for name, body in bodies.items()
        }
    assert statuses == {"malformed": 400, "unterminated": 400}
    assert forwarded == []


def test_an_upload_holds_one_admission_slot_from_parsing_through_the_team_hop(monkeypatch):
    """A saturated upload budget refuses before reading the body; a slot is held until Team answers."""
    monkeypatch.setattr(authn, "authed_account_bounded", _session())
    admission = threading.BoundedSemaphore(1)
    monkeypatch.setattr(files, "UPLOAD_ADMISSION", admission)
    read = []
    original = Request.stream

    def recording(self):
        read.append(self.url.path)
        return original(self)

    held_during_hop = []

    async def upstream(*_args, **_kwargs):
        held_during_hop.append(not admission.acquire(blocking=False))
        return 503, {"detail": "unavailable"}

    monkeypatch.setattr(Request, "stream", recording)
    monkeypatch.setattr(files, "call_raw_bounded", upstream)
    body = {"file": ("file.txt", b"data", "text/plain")}
    with TestClient(app) as client:
        assert admission.acquire(blocking=False)
        saturated = client.post("/api/teams/team/files", files=body, headers=ORIGIN)
        assert read == []
        admission.release()
        forwarded = client.post("/api/teams/team/files", files=body, headers=ORIGIN)
        refused = client.post("/api/teams/team/files", content=b"raw", headers=ORIGIN)
    assert saturated.status_code == 429
    assert saturated.headers["retry-after"] == "1"
    assert saturated.headers["cache-control"] == "private, no-store"
    assert (forwarded.status_code, refused.status_code) == (503, 400)
    assert held_during_hop == [True]
    assert admission.acquire(blocking=False)
