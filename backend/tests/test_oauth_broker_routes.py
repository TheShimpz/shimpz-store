from __future__ import annotations

from contextlib import contextmanager
from unittest import mock

from fastapi.testclient import TestClient

from app import main
from app.oauth_broker import SCOPES, OAuthOutOfBand, OAuthRedirect
from app.routers import oauth


class _Broker:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def start(self, **values) -> str:
        self.calls.append(("start", values))
        return "https://dash.cloudflare.com/oauth2/auth?validated=1"

    def callback(self, **values) -> OAuthRedirect:
        self.calls.append(("callback", values))
        return OAuthRedirect(
            "http://127.0.0.1:7777/api/oauth/cloudflare/callback?state=" + "s" * 43 + "&claim=" + "a" * 64
        )

    def claim(self, **values) -> dict[str, object]:
        self.calls.append(("claim", values))
        return {
            "access_token": "access-token-private-123456",
            "refresh_token": "refresh-token-private-123456",
            "expires_in": 3600,
            "scopes": list(SCOPES),
            "broker_lease": "lease-private-123456",
        }

    def refresh(self, **values) -> dict[str, object]:
        self.calls.append(("refresh", values))
        return {
            "access_token": "refreshed-access-token-private-123456",
            "refresh_token": "refreshed-refresh-token-private-123456",
            "expires_in": 3600,
            "scopes": list(SCOPES),
            "broker_lease": "refreshed-lease-private-123456",
        }

    def revoke(self, **values) -> None:
        self.calls.append(("revoke", values))


@contextmanager
def _broker():
    broker = _Broker()
    with mock.patch.object(oauth, "_BROKER", broker):
        yield broker


def test_browser_start_and_callback_redirect_without_oauth_tokens() -> None:
    with _broker() as broker, TestClient(main.app) as client:
        start = client.get(
            "/api/oauth/cloudflare/start",
            params={
                "state": "s" * 43,
                "code_challenge": "c" * 43,
                "scope": " ".join(SCOPES),
                "callback": "loopback",
            },
            follow_redirects=False,
        )
        callback = client.get(
            "/api/oauth/cloudflare/callback",
            params={
                "state": "b" * 43,
                "code": "authorization-code-private-123456",
                "scope": " ".join(SCOPES),
            },
            follow_redirects=False,
        )

    assert start.status_code == 303
    assert start.headers["location"].startswith("https://dash.cloudflare.com/oauth2/auth?")
    assert callback.status_code == 303
    assert callback.headers["location"].startswith("http://127.0.0.1:7777/api/oauth/cloudflare/callback?")
    assert "access-token" not in callback.headers["location"]
    assert "refresh-token" not in callback.headers["location"]
    assert start.headers["cache-control"] == "private, no-store"
    assert callback.headers["referrer-policy"] == "no-referrer"
    assert [call[0] for call in broker.calls] == ["start", "callback"]
    assert broker.calls[0][1]["callback_mode"] == "loopback"


def test_browser_start_requires_an_explicit_callback_mode() -> None:
    with _broker() as broker, TestClient(main.app) as client:
        response = client.get(
            "/api/oauth/cloudflare/start",
            params={
                "state": "s" * 43,
                "code_challenge": "c" * 43,
                "scope": " ".join(SCOPES),
            },
            follow_redirects=False,
        )

    assert response.status_code == 400
    assert broker.calls == []


def test_browser_callback_requires_the_closed_cloudflare_scope_envelope() -> None:
    invalid_queries = (
        {"state": "b" * 43, "code": "authorization-code-private-123456"},
        {
            "state": "b" * 43,
            "code": "authorization-code-private-123456",
            "scope": " ".join(SCOPES),
            "token": "must-not-cross",
        },
    )
    with _broker() as broker, TestClient(main.app) as client:
        responses = [
            client.get(
                "/api/oauth/cloudflare/callback",
                params=query,
                follow_redirects=False,
            )
            for query in invalid_queries
        ]
        duplicate = client.get(
            "/api/oauth/cloudflare/callback?state="
            + "b" * 43
            + "&code=first&code=second&scope=dns.read+dns.write+offline_access+zone.read",
            follow_redirects=False,
        )

    assert all(response.status_code == 400 for response in [*responses, duplicate])
    assert broker.calls == []


def test_browser_routes_forward_the_canonical_read_only_scope_subset() -> None:
    read_scopes = ("dns.read", "offline_access", "zone.read")
    with _broker() as broker, TestClient(main.app) as client:
        start = client.get(
            "/api/oauth/cloudflare/start",
            params={
                "state": "s" * 43,
                "code_challenge": "c" * 43,
                "scope": " ".join(read_scopes),
                "callback": "loopback",
            },
            follow_redirects=False,
        )
        callback = client.get(
            "/api/oauth/cloudflare/callback",
            params={
                "state": "b" * 43,
                "code": "authorization-code-private-123456",
                "scope": " ".join(read_scopes),
            },
            follow_redirects=False,
        )

    assert start.status_code == callback.status_code == 303
    assert broker.calls[0][1]["scopes"] == list(read_scopes)
    assert broker.calls[1][1]["scopes"] == list(read_scopes)


def test_browser_start_forwards_only_the_named_hosted_admin_callback() -> None:
    with _broker() as broker, TestClient(main.app) as client:
        start = client.get(
            "/api/oauth/cloudflare/start",
            params={
                "state": "s" * 43,
                "code_challenge": "c" * 43,
                "scope": " ".join(SCOPES),
                "callback": "hosted",
            },
            follow_redirects=False,
        )

    assert start.status_code == 303
    assert broker.calls == [
        (
            "start",
            {
                "local_state": "s" * 43,
                "local_code_challenge": "c" * 43,
                "callback_mode": "hosted",
                "scopes": list(SCOPES),
            },
        )
    ]


def test_out_of_band_callback_renders_only_a_hardened_completion_code() -> None:
    with (
        _broker() as broker,
        mock.patch.object(
            broker,
            "callback",
            return_value=OAuthOutOfBand("c1." + "s" * 43 + "." + "a" * 64),
        ),
        TestClient(main.app) as client,
    ):
        start = client.get(
            "/api/oauth/cloudflare/start",
            params={
                "state": "s" * 43,
                "code_challenge": "c" * 43,
                "scope": " ".join(SCOPES),
                "callback": "out-of-band",
            },
            follow_redirects=False,
        )
        callback = client.get(
            "/api/oauth/cloudflare/callback",
            params={
                "state": "b" * 43,
                "code": "authorization-code-private-123456",
                "scope": " ".join(SCOPES),
            },
            follow_redirects=False,
        )

    assert start.status_code == 303
    assert callback.status_code == 200
    assert callback.headers["content-type"].startswith("text/html")
    assert callback.headers["cache-control"] == "private, no-store"
    assert callback.headers["referrer-policy"] == "no-referrer"
    assert callback.headers["cross-origin-opener-policy"] == "same-origin"
    assert "default-src 'none'" in callback.headers["content-security-policy"]
    assert "c1." + "s" * 43 + "." + "a" * 64 in callback.text
    assert "access-token" not in callback.text
    assert "refresh-token" not in callback.text
    assert "location" not in callback.headers


def test_browser_start_rejects_an_arbitrary_callback_before_the_broker() -> None:
    with _broker() as broker, TestClient(main.app) as client:
        response = client.get(
            "/api/oauth/cloudflare/start",
            params={
                "state": "s" * 43,
                "code_challenge": "c" * 43,
                "scope": " ".join(SCOPES),
                "callback": "https://evil.example",
            },
            follow_redirects=False,
        )

    assert response.status_code == 400
    assert broker.calls == []


def test_server_only_claim_refresh_and_revoke_are_exact_and_no_store() -> None:
    with _broker() as broker, TestClient(main.app) as client:
        claim = client.post(
            "/api/oauth/cloudflare/claim",
            json={"claim": "a" * 64, "state": "s" * 43, "code_verifier": "v" * 43},
        )
        refresh = client.post(
            "/api/oauth/cloudflare/refresh",
            json={
                "refresh_token": "refresh-token-private-123456",
                "broker_lease": "lease-private-123456",
                "scopes": list(SCOPES),
            },
        )
        revoke = client.post(
            "/api/oauth/cloudflare/revoke",
            json={
                "token": "access-token-private-123456",
                "broker_lease": "lease-private-123456",
            },
        )

    assert claim.status_code == refresh.status_code == revoke.status_code == 200
    assert claim.headers["cache-control"] == "private, no-store"
    assert set(claim.json()) == {
        "access_token",
        "refresh_token",
        "expires_in",
        "scopes",
        "broker_lease",
    }
    assert revoke.json() == {"revoked": True}
    assert [call[0] for call in broker.calls] == ["claim", "refresh", "revoke"]


def test_token_routes_reject_browser_origin_duplicate_and_extra_fields() -> None:
    with _broker() as broker, TestClient(main.app) as client:
        browser = client.post(
            "/api/oauth/cloudflare/claim",
            headers={"Origin": "https://evil.example"},
            json={"claim": "a" * 64, "state": "s" * 43, "code_verifier": "v" * 43},
        )
        duplicate = client.post(
            "/api/oauth/cloudflare/claim",
            headers={"Content-Type": "application/json"},
            content=b'{"claim":"first","claim":"second","state":"'
            + b"s" * 43
            + b'","code_verifier":"'
            + b"v" * 43
            + b'"}',
        )
        extra = client.post(
            "/api/oauth/cloudflare/revoke",
            json={
                "token": "private-token-123456",
                "broker_lease": "private-lease-123456",
                "extra": True,
            },
        )

    assert browser.status_code == 403
    assert duplicate.status_code == 400
    assert extra.status_code == 400
    assert broker.calls == []
