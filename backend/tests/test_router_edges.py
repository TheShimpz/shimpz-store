"""Edge coverage for the Store's small HTTP route adapters."""

from __future__ import annotations

import asyncio
import secrets

import pytest
from fastapi.testclient import TestClient

from app import authn
from app.main import app
from app.payloads import ClientPayloadError
from app.routers import account, assistant_lifecycle, static, teams


def _session(account_id: str = "account", username: str = "user"):
    token = secrets.token_hex(16)

    async def authenticated(_request):
        return token, account_id, username

    return authenticated


def test_account_bounded_adapter_uses_the_dedicated_executor(monkeypatch):
    captured = []

    async def call(executor, *args, **kwargs):
        captured.append((executor, args, kwargs))
        return 200, {"ok": True}

    monkeypatch.setattr(account, "call_bounded", call)
    assert asyncio.run(account._bounded_call("url", "GET", "/path")) == (200, {"ok": True})
    assert captured == [(authn.EXECUTOR, ("url", "GET", "/path"), {})]


def test_account_routes_set_and_clear_cookie_and_project_me(monkeypatch):
    async def credentials(*_args, **_kwargs):
        return 200, {"account_id": "account", "username": "user", "token": "opaque"}

    monkeypatch.setattr(account, "_bounded_call", credentials)
    monkeypatch.setattr(authn, "authed_account_bounded", _session())
    with TestClient(app) as client:
        signup = client.post("/api/signup", json={"username": "user", "password": "secret"})
        login = client.post("/api/login", json={"username": "user", "password": "secret"})
        me = client.get("/api/me")
        logout = client.post("/api/logout")
    for response in (signup, login):
        assert response.status_code == 200
        assert response.json() == {"account_id": "account", "username": "user"}
        assert response.headers["set-cookie"].startswith("shimpz_account=opaque;")
    assert me.json() == {"authenticated": True, "account_id": "account", "username": "user"}
    assert logout.json() == {"ok": True}
    assert "Max-Age=0" in logout.headers["set-cookie"]


@pytest.mark.parametrize(
    "payload",
    [
        {"team_name": "!!!", "provider": "openai", "model": "gpt-5.6-luna"},
        {"team_name": "Marketing", "provider": "unknown", "model": "model"},
    ],
)
def test_team_creation_rejects_invalid_identity_or_provider(payload):
    with pytest.raises(ClientPayloadError):
        teams._create_payload(payload, "account")


def test_team_routes_cover_unauthenticated_and_forwarded_paths(monkeypatch):
    async def unauthenticated(_request):
        return "", "", ""

    monkeypatch.setattr(authn, "authed_account_bounded", unauthenticated)
    with TestClient(app) as client:
        assert client.get("/api/teams").status_code == 401
        assert client.post("/api/teams", json={}).status_code == 401
        assert client.delete("/api/teams/team").status_code == 401

    calls = []

    async def forwarded(_executor, _url, method, path, *args, **kwargs):
        calls.append((method, path, args, kwargs))
        return 200, {"ok": True}

    monkeypatch.setattr(authn, "authed_account_bounded", _session())
    monkeypatch.setattr(teams, "call_bounded", forwarded)
    with TestClient(app) as client:
        listing = client.get("/api/teams")
        deletion = client.delete("/api/teams/team")
    assert listing.json() == {"ok": True}
    assert deletion.json() == {"ok": True}
    assert [(method, path) for method, path, *_rest in calls] == [
        ("GET", "/v1/teams"),
        ("DELETE", "/v1/teams/team"),
    ]


def test_inference_routes_reject_unauthenticated_and_invalid_configuration(monkeypatch):
    async def unauthenticated(_request):
        return "", "", ""

    monkeypatch.setattr(authn, "authed_account_bounded", unauthenticated)
    with TestClient(app) as client:
        assert client.get("/api/teams/team/inference").status_code == 401
        assert client.put("/api/teams/team/inference", json={}).status_code == 401

    monkeypatch.setattr(authn, "authed_account_bounded", _session())
    with TestClient(app) as client:
        wrong_shape = client.put("/api/teams/team/inference", json={"provider": "openai"})
        bad_provider = client.put("/api/teams/team/inference", json={"provider": "unknown", "model": "model"})
    assert wrong_shape.status_code == 400
    assert bad_provider.status_code == 400


def test_assistant_routes_reject_noncanonical_ids_before_upstream(monkeypatch):
    monkeypatch.setattr(authn, "authed_account_bounded", _session())
    with TestClient(app) as client:
        listing = client.get("/api/teams/Invalid/assistants")
        install = client.post(
            "/api/teams/team/assistants",
            json={"assistant_id": "Invalid", "source_digest": "sha256:" + "a" * 64},
            headers={"Origin": "https://shimpz.com"},
        )
        uninstall = client.delete(
            "/api/teams/team/assistants/Invalid",
            headers={"Origin": "https://shimpz.com"},
        )
    assert listing.status_code == 400
    assert install.status_code == 400
    assert uninstall.status_code == 400


def test_assistant_id_pair_rejects_an_invalid_assistant():
    with pytest.raises(ClientPayloadError, match="Assistant"):
        assistant_lifecycle._canonical_ids("team", "Invalid")


def test_public_icon_and_static_resolution_reject_invalid_paths():
    with TestClient(app) as client:
        assert client.get("/api/assistant-icons/not-a-hash/not-a-hash.png").status_code == 503
    assert static.resolve("../secret") is None
