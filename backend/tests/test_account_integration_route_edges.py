"""Failure coverage for Account-backed Store integration routes."""

from __future__ import annotations

import asyncio
import json
import secrets

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app import authn
from app.main import app
from app.oauth_broker import SCOPES, OAuthBrokerError
from app.routers import model_providers, oauth, action_assurance


def _session(authenticated: bool = True):
    token = secrets.token_hex(16) if authenticated else ""

    async def current(_request):
        return token, "account" if token else "", "user" if token else ""

    return current


def _request(body: bytes, headers: list[tuple[bytes, bytes]]) -> Request:
    delivered = False

    async def receive():
        nonlocal delivered
        if delivered:
            return {"type": "http.disconnect"}
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request({"type": "http", "headers": headers}, receive)


def test_model_provider_routes_reject_unauthenticated_requests(monkeypatch):
    monkeypatch.setattr(authn, "authed_account_bounded", _session(False))
    with TestClient(app) as client:
        listing = client.get("/api/model-providers")
        upsert = client.post("/api/model-providers/openai", json={})
        deletion = client.delete("/api/model-providers/openai")
    assert [response.status_code for response in (listing, upsert, deletion)] == [401, 401, 401]


def test_model_provider_listing_forwards_failure_and_rejects_invalid_inventory(monkeypatch):
    monkeypatch.setattr(authn, "authed_account_bounded", _session())
    responses = iter(((503, {"detail": "unavailable"}), (200, {})))

    async def upstream(*_args, **_kwargs):
        return next(responses)

    monkeypatch.setattr(model_providers, "call_bounded", upstream)
    with TestClient(app) as client:
        unavailable = client.get("/api/model-providers")
        invalid = client.get("/api/model-providers")
    assert unavailable.status_code == 503
    assert invalid.status_code == 502


def test_model_provider_mutations_reject_shape_and_unknown_provider(monkeypatch):
    monkeypatch.setattr(authn, "authed_account_bounded", _session())
    with TestClient(app) as client:
        wrong_shape = client.post("/api/model-providers/openai", json={"auth_type": "api_key"})
        unknown = client.delete("/api/model-providers/unknown")
    assert wrong_shape.status_code == 400
    assert unknown.status_code == 400


def test_model_provider_revocation_rejects_invalid_state_and_forwards_begin_failure(monkeypatch):
    with pytest.raises(ValueError, match="invalid state"):
        model_providers._revocation_state({"already_absent": False, "generation": True})

    responses = iter(((503, {"detail": "unavailable"}), (200, {"already_absent": False})))
    monkeypatch.setattr(model_providers, "call", lambda *_args, **_kwargs: next(responses))
    unavailable = model_providers._delete_model_provider_for_token("token", "openai", "127.0.0.1")
    invalid = model_providers._delete_model_provider_for_token("token", "openai", "127.0.0.1")
    assert unavailable.status_code == 503
    assert invalid.status_code == 502


def test_model_provider_revocation_projects_an_already_absent_secret(monkeypatch):
    monkeypatch.setattr(
        model_providers,
        "call",
        lambda *_args, **_kwargs: (200, {"already_absent": True, "generation": None}),
    )
    response = model_providers._delete_model_provider_for_token("token", "openai", "127.0.0.1")
    assert response.status_code == 200
    assert json.loads(response.body) == {
        "provider": "openai",
        "generation": None,
        "deleted": False,
        "already_absent": True,
    }


def test_action_assurance_error_categories_and_invalid_descriptors():
    assert action_assurance._public_error(429).status_code == 429
    assert action_assurance._public_error(400).status_code == 400
    assert action_assurance._credential_descriptor(None) is None
    assert action_assurance._options_response(403, {}).status_code == 403
    assert action_assurance._options_response(200, {}).status_code == 502


def test_action_assurance_rejects_non_object_account_response(monkeypatch):
    monkeypatch.setattr(authn, "authed_account_bounded", _session())

    async def invalid(*_args, **_kwargs):
        return 200, []

    monkeypatch.setattr(action_assurance, "call_bounded", invalid)
    with TestClient(app) as client:
        response = client.post(
            "/api/security/action-assurance/password",
            json={"team_id": "team", "challenge_id": "a" * 32, "password": "secret"},
            headers={"Origin": "https://shimpz.com"},
        )
    assert response.status_code == 502


def test_oauth_body_requires_an_explicit_length():
    request = _request(b"{}", [(b"content-type", b"application/json")])
    with pytest.raises(Exception) as exc:
        asyncio.run(oauth._body(request, frozenset()))
    assert getattr(exc.value, "status", None) == 411


def test_oauth_start_and_callback_translate_broker_failures(monkeypatch):
    async def fail(*_args, **_kwargs):
        raise OAuthBrokerError("failed")

    monkeypatch.setattr(oauth, "_run_bounded", fail)
    scope = " ".join(SCOPES)
    with TestClient(app) as client:
        start = client.get(
            "/api/oauth/cloudflare/start",
            params={
                "state": "state",
                "code_challenge": "challenge",
                "scope": scope,
                "callback": "hosted",
            },
        )
        callback = client.get(
            "/api/oauth/cloudflare/callback",
            params={"state": "state", "code": "code", "scope": scope},
        )
    assert start.status_code == 502
    assert callback.status_code == 502


def test_oauth_callback_and_unknown_post_reject_unexpected_results(monkeypatch):
    async def unexpected(*_args, **_kwargs):
        return object()

    monkeypatch.setattr(oauth, "_run_bounded", unexpected)
    scope = " ".join(SCOPES)
    with TestClient(app) as client:
        callback = client.get(
            "/api/oauth/cloudflare/callback",
            params={"state": "state", "code": "code", "scope": scope},
        )
    assert callback.status_code == 502

    request = _request(
        b"{}",
        [(b"content-type", b"application/json"), (b"content-length", b"2")],
    )
    unknown = asyncio.run(oauth._post(request, "unknown", frozenset()))
    assert unknown.status_code == 502
