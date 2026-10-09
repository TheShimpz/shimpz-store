import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app


def test_health():
    with TestClient(app) as client:
        resp = client.get("/api/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_only_the_assistant_embed_allows_named_admin_origins():
    with TestClient(app) as client:
        normal = client.get("/api/health")
        assert normal.headers["x-frame-options"] == "DENY"
        assert "frame-ancestors 'none'" in normal.headers["content-security-policy"]
        assert "frame-src 'none'" in normal.headers["content-security-policy"]
        assert "youtube" not in normal.headers["content-security-policy"]
        assert "x-robots-tag" not in normal.headers

        for locale in ("en", "pt", "es", "zh", "fr", "de", "ja", "ar"):
            embedded = client.get(f"/{locale}/assistants/embed")
            policy = embedded.headers["content-security-policy"]
            assert "x-frame-options" not in embedded.headers
            ancestors = policy.split("frame-ancestors ", 1)[1].split(";", 1)[0]
            assert ancestors == ("http://127.0.0.1:* http://localhost:* http://[::1]:* https://local.shimpz.com")
            assert embedded.headers["x-robots-tag"] == "noindex, nofollow"

        lookalike = client.get("/en/assistants/embed/anything")
        assert lookalike.headers["x-frame-options"] == "DENY"
        assert "frame-ancestors 'none'" in lookalike.headers["content-security-policy"]


def test_retired_space_apis_are_not_routed():
    """Store routes only its public catalog, the OAuth broker, and the static site; Space APIs answer as absent."""
    retired = (
        ("POST", "/api/login"),
        ("GET", "/api/me"),
        ("GET", "/api/teams"),
        ("POST", "/api/teams"),
        ("GET", "/api/teams/team/assistants"),
        ("GET", "/api/teams/team/files"),
        ("PUT", "/api/teams/team/inference"),
        ("GET", "/api/model-providers"),
        ("POST", "/api/security/action-assurance/password"),
    )
    with TestClient(app) as client:
        statuses = [client.request(method, path).status_code for method, path in retired]
        with pytest.raises(WebSocketDisconnect), client.websocket_connect("/api/teams/team/chat/ws"):
            pass
    # Only the static GET fallback matches these paths: a GET finds no file, and any other method has no route.
    assert statuses == [405 if method != "GET" else 404 for method, _path in retired]
