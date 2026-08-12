from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.routers import action_assurance

TEAM_ID = "team_1"
CHALLENGE_ID = "a" * 32
HANDLE = "b" * 43
ORIGIN = next(iter(config.ASSISTANT_MUTATION_ALLOWED_ORIGINS))


@pytest.fixture
def client(monkeypatch):
    async def authed(_request):
        return "session-token", "account-one", "owner"

    monkeypatch.setattr(action_assurance.authn, "authed_account_bounded", authed)
    with TestClient(app) as value:
        yield value


@pytest.mark.parametrize(
    ("suffix", "factor", "value"),
    [
        ("password", "password", "correct horse battery staple"),
        ("totp", "code", "123456"),
        (
            "webauthn/confirm",
            "credential",
            {
                "id": "credential",
                "rawId": "credential",
                "type": "public-key",
                "response": {
                    "clientDataJSON": "client-data",
                    "authenticatorData": "authenticator-data",
                    "signature": "signature",
                },
            },
        ),
    ],
)
def test_factor_routes_transit_only_exact_session_bound_payload(
    client,
    monkeypatch,
    suffix: str,
    factor: str,
    value: object,
):
    calls = []

    async def account_call(*args, **kwargs):
        calls.append((args, kwargs))
        return 200, {"version": 1, "handle": HANDLE, "expires_in": 300}

    monkeypatch.setattr(action_assurance, "call_bounded", account_call)
    response = client.post(
        f"/api/security/action-assurance/{suffix}",
        headers={"origin": ORIGIN},
        json={"team_id": TEAM_ID, "challenge_id": CHALLENGE_ID, factor: value},
    )

    assert response.status_code == 200
    assert response.json() == {"version": 1, "handle": HANDLE, "expires_in": 300}
    assert response.headers["cache-control"] == "private, no-store"
    args, kwargs = calls[0]
    assert args[1:4] == (
        config.ACCOUNT_URL,
        "POST",
        f"/v1/security/action-assurance/{suffix}",
    )
    assert args[4] == {
        "token": "session-token",
        "team_id": TEAM_ID,
        "challenge_id": CHALLENGE_ID,
        factor: value,
    }
    assert kwargs["extra"]["X-Forwarded-For"]


def test_webauthn_options_projects_only_browser_ceremony_fields(client, monkeypatch):
    options = {
        "challenge": "c" * 43,
        "timeout": 300_000,
        "rpId": "shimpz.com",
        "allowCredentials": [{"id": "d" * 43, "type": "public-key"}],
        "userVerification": "required",
    }

    async def account_call(*_args, **_kwargs):
        return 200, options

    monkeypatch.setattr(action_assurance, "call_bounded", account_call)
    response = client.post(
        "/api/security/action-assurance/webauthn/options",
        headers={"origin": ORIGIN},
        json={"team_id": TEAM_ID, "challenge_id": CHALLENGE_ID},
    )

    assert response.status_code == 200
    assert response.json() == options


def test_action_assurance_rejects_cross_origin_before_authentication(monkeypatch):
    async def must_not_authenticate(_request):
        raise AssertionError("authentication must not run")

    monkeypatch.setattr(
        action_assurance.authn,
        "authed_account_bounded",
        must_not_authenticate,
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/security/action-assurance/password",
            headers={"origin": "https://attacker.example"},
            json={
                "team_id": TEAM_ID,
                "challenge_id": CHALLENGE_ID,
                "password": "must-not-be-read",
            },
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "origin is not allowed"}


def test_action_assurance_requires_a_current_account_session(monkeypatch):
    async def anonymous(_request):
        return "", "", ""

    monkeypatch.setattr(action_assurance.authn, "authed_account_bounded", anonymous)
    with TestClient(app) as client:
        response = client.post(
            "/api/security/action-assurance/totp",
            headers={"origin": ORIGIN},
            json={"team_id": TEAM_ID, "challenge_id": CHALLENGE_ID, "code": "123456"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "not authenticated"}


@pytest.mark.parametrize("expires_in", [1, 120, 300])
def test_action_assurance_accepts_bounded_account_owned_handle_expiry(
    client,
    monkeypatch,
    expires_in: int,
):
    async def account_call(*_args, **_kwargs):
        return 200, {"version": 1, "handle": HANDLE, "expires_in": expires_in}

    monkeypatch.setattr(action_assurance, "call_bounded", account_call)
    response = client.post(
        "/api/security/action-assurance/password",
        headers={"origin": ORIGIN},
        json={
            "team_id": TEAM_ID,
            "challenge_id": CHALLENGE_ID,
            "password": "factor-never-reflected",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"version": 1, "handle": HANDLE, "expires_in": expires_in}


@pytest.mark.parametrize(
    "payload",
    [
        {"team_id": TEAM_ID, "challenge_id": "short", "password": "secret"},
        {
            "team_id": TEAM_ID,
            "challenge_id": CHALLENGE_ID,
            "password": "secret",
            "kind": "auth:phishing-resistant",
        },
    ],
)
def test_action_assurance_rejects_noncanonical_bindings_before_factor_transit(
    client,
    monkeypatch,
    payload: dict,
):
    async def must_not_call(*_args, **_kwargs):
        raise AssertionError("factor must not cross")

    monkeypatch.setattr(action_assurance, "call_bounded", must_not_call)
    response = client.post(
        "/api/security/action-assurance/password",
        headers={"origin": ORIGIN},
        json=payload,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid Action assurance request"}


@pytest.mark.parametrize(
    "assurance_case",
    [
        (401, {"error": "private password marker"}, 401, "authentication was not confirmed"),
        (503, {"error": "private database marker"}, 503, "authentication is temporarily unavailable"),
        (
            200,
            {"version": 1, "handle": HANDLE, "expires_in": 300, "secret": "private"},
            502,
            "authentication is temporarily unavailable",
        ),
        (
            200,
            {"version": 1, "handle": HANDLE, "expires_in": 301},
            502,
            "authentication is temporarily unavailable",
        ),
        (
            200,
            {"version": 1, "handle": HANDLE, "expires_in": True},
            502,
            "authentication is temporarily unavailable",
        ),
    ],
)
def test_action_assurance_redacts_failures_and_rejects_expanded_successes(
    client,
    monkeypatch,
    assurance_case: tuple[int, dict, int, str],
):
    status, body, expected_status, expected_detail = assurance_case

    async def account_call(*_args, **_kwargs):
        return status, body

    monkeypatch.setattr(action_assurance, "call_bounded", account_call)
    response = client.post(
        "/api/security/action-assurance/password",
        headers={"origin": ORIGIN},
        json={
            "team_id": TEAM_ID,
            "challenge_id": CHALLENGE_ID,
            "password": "factor-never-reflected",
        },
    )

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert "private" not in response.text
    assert "factor-never-reflected" not in response.text
