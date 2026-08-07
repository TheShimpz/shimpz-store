"""Failure coverage for opaque Team file routes."""

from __future__ import annotations

import secrets

from fastapi.testclient import TestClient

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
        monkeypatch.setattr(files, "MAX_UPLOAD_BYTES", files.team_contract.MAX_FILE_UPLOAD_BYTES)
        invalid = client.post(
            "/api/teams/team/files",
            files={"file": ("../file.txt", b"data", "text/plain")},
            headers=ORIGIN,
        )
    assert bad_team.status_code == 400
    assert oversized.status_code == 413
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
