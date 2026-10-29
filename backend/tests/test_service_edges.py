"""Service-level failure and configuration edge coverage."""

import asyncio
from types import SimpleNamespace

import structlog
from fastapi.testclient import TestClient

from app import logconf, main
from app.concurrency import ExecutorSaturatedError
from app.routers import static


def test_logged_exceptions_never_render_frame_locals(capsys):
    """An exception's stack is logged, but the values of its frame's variables (tokens, upload bytes) never are."""
    logconf.setup("test")
    structlog.reset_defaults()
    logconf.setup("test")

    def upload(token: str, data: bytes) -> None:
        raise RuntimeError("malformed multipart")

    # The secrets come from variables, so only a dump of frame locals could put them in the rendered log.
    token, data = "session-" + "token-must-not-log", b"upload-" + b"bytes-must-not-log"
    try:
        upload(token, data)
    except RuntimeError:
        structlog.get_logger().exception("unhandled_exception")
    rendered = capsys.readouterr().out
    assert "malformed multipart" in rendered
    assert "session-token-must-not-log" not in rendered
    assert "upload-bytes-must-not-log" not in rendered


def test_application_exception_handlers_return_closed_responses():
    request = SimpleNamespace(url=SimpleNamespace(path="/private"))
    unhandled = asyncio.run(main.unhandled(request, RuntimeError("private failure")))
    assert unhandled.status_code == 500
    assert unhandled.body == b'{"detail":"internal server error"}'

    saturated = asyncio.run(main.executor_saturated(request, ExecutorSaturatedError("full")))
    assert saturated.status_code == 429
    assert saturated.headers["retry-after"] == "1"
    assert saturated.body == b'{"detail":"Store upstream capacity reached"}'


def test_an_unhandled_failure_answers_with_the_security_headers_and_the_request_id(monkeypatch):
    """The 500 leaves through the header layer like every other response, so it is never framed or sniffed."""

    def fail(_path: str) -> None:
        raise RuntimeError("private failure")

    monkeypatch.setattr(static, "resolve", fail)
    with TestClient(main.app, raise_server_exceptions=False) as client:
        response = client.get("/en", headers={"X-Request-ID": "trace-500"})

    assert response.status_code == 500
    assert response.content == b'{"detail":"internal server error"}'
    assert response.headers["x-request-id"] == "trace-500"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
