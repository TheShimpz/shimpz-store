"""Service-level failure and configuration edge coverage."""

import asyncio
from types import SimpleNamespace

import pytest
import structlog

from app import logconf, main
from app.concurrency import ExecutorSaturatedError


def test_logging_rejects_unknown_levels(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "verbose")
    with pytest.raises(ValueError, match="invalid LOG_LEVEL"):
        logconf.setup("test")


def test_logging_supports_the_console_renderer(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("LOG_FORMAT", "console")
    logconf.setup("test")


@pytest.mark.parametrize("log_format", ["json", "console"])
def test_logged_exceptions_never_render_frame_locals(monkeypatch, capsys, log_format):
    """An exception's stack is logged, but the values of its frame's variables (tokens, upload bytes) never are."""
    monkeypatch.setenv("LOG_LEVEL", "info")
    monkeypatch.setenv("LOG_FORMAT", log_format)
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
