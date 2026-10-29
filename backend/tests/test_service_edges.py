"""Service-level failure and configuration edge coverage."""

import asyncio
import json
import logging.config
from pathlib import Path
from types import SimpleNamespace

import pytest
import structlog
from fastapi.testclient import TestClient

from app import logconf, main
from app.concurrency import ExecutorSaturatedError
from app.routers import static


def test_logged_exceptions_never_render_frame_locals(capsys):
    """An exception is logged by its class and frame locations, never by its message or its frames' values."""
    logconf.setup("test")
    structlog.reset_defaults()
    logconf.setup("test")

    def upload(token: str, data: bytes) -> None:
        raise RuntimeError("malformed multipart PRIVATE_SENTINEL")

    # The secrets come from variables, so only a dump of frame locals could put them in the rendered log.
    token, data = "session-" + "token-must-not-log", b"upload-" + b"bytes-must-not-log"
    try:
        upload(token, data)
    except RuntimeError:
        structlog.get_logger().exception("unhandled_exception")
    line = json.loads(capsys.readouterr().out)
    assert line["msg"] == "unhandled_exception"
    assert line["exception"] == "RuntimeError"
    assert line["frames"][-1].endswith(":upload")
    rendered = json.dumps(line)
    assert "PRIVATE_SENTINEL" not in rendered
    assert "session-token-must-not-log" not in rendered
    assert "upload-bytes-must-not-log" not in rendered


@pytest.mark.parametrize(
    "exc_info",
    [
        lambda error: error,
        lambda error: (type(error), error, error.__traceback__),
        lambda _error: True,
    ],
)
def test_every_exception_form_is_summarized_by_its_class(exc_info):
    try:
        raise ValueError("PRIVATE_SENTINEL")
    except ValueError as error:
        summary = logconf.exception_summary(None, "error", {"msg": "event", "exc_info": exc_info(error)})

    assert summary["exception"] == "ValueError"
    assert summary["frames"][-1].endswith(":test_every_exception_form_is_summarized_by_its_class")
    assert "PRIVATE_SENTINEL" not in json.dumps(summary)
    assert logconf.exception_summary(None, "info", {"msg": "event", "exc_info": False}) == {"msg": "event"}
    assert logconf.exception_summary(None, "info", {"msg": "event", "exc_info": True}) == {"msg": "event"}


def test_the_server_loggers_write_only_json_templates_on_stdout(capsys):
    """The server's own lines name their template and exception class, never their arguments or exception text."""
    config = json.loads((Path(logconf.__file__).parent / "logging.json").read_text(encoding="utf-8"))
    logging.config.dictConfig(config)
    server = logging.getLogger("uvicorn.error")
    server.info("Started server process [%d] %s", 7, "PRIVATE_SENTINEL")
    try:
        raise RuntimeError("PRIVATE_SENTINEL")
    except RuntimeError:
        server.exception("Exception in ASGI application\n")
    logging.getLogger("uvicorn").warning(RuntimeError("PRIVATE_SENTINEL"))

    captured = capsys.readouterr()
    lines = [json.loads(line) for line in captured.out.splitlines()]
    assert captured.err == ""
    assert [(line["level"], line["msg"], line.get("exception")) for line in lines] == [
        ("info", "Started server process [%d] %s", None),
        ("error", "Exception in ASGI application\n", "RuntimeError"),
        ("warning", "RuntimeError", None),
    ]
    assert all(line["service"] == "shimpz-store" and line["ts"].endswith("Z") for line in lines)
    assert "PRIVATE_SENTINEL" not in captured.out


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
