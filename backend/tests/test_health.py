from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        resp = client.get("/api/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_every_response_refuses_framing():
    with TestClient(app) as client:
        for path in ("/api/health", "/en/assistants", "/pt"):
            response = client.get(path)
            assert response.headers["x-frame-options"] == "DENY"
            assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
            assert "frame-src 'none'" in response.headers["content-security-policy"]
