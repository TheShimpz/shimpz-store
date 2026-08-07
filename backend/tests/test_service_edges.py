"""Service-level failure and configuration edge coverage."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi.responses import JSONResponse

from app import authn, logconf, main
from app.concurrency import ExecutorSaturatedError
from app.config import ACCOUNT_COOKIE
from app.payloads import ClientPayloadError


def test_account_cookie_uses_the_closed_security_attributes():
    response = JSONResponse({"ok": True})
    authn.set_cookie(response, "opaque-token")
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{ACCOUNT_COOKIE}=opaque-token;")
    assert "HttpOnly" in cookie
    assert "Path=/" in cookie
    assert "SameSite=strict" in cookie
    assert "Secure" in cookie


def test_account_authentication_rejects_an_upstream_denial(monkeypatch):
    monkeypatch.setattr(authn, "verification_capability", lambda: "c" * 64)
    monkeypatch.setattr(authn, "call", lambda *_args, **_kwargs: (403, {"detail": "denied"}))
    request = SimpleNamespace(cookies={ACCOUNT_COOKIE: "opaque-token"})
    assert authn.authed_account(request) == ("", "", "")


def test_account_authentication_rejects_a_missing_cookie():
    request = SimpleNamespace(cookies={})
    assert authn.authed_account(request) == ("", "", "")


def test_verification_capability_handles_an_open_failure(monkeypatch):
    def fail_open(*_args, **_kwargs):
        raise OSError("unavailable")

    monkeypatch.setattr(authn.os, "open", fail_open)
    assert authn.verification_capability() == ""


def test_logging_rejects_unknown_levels(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "verbose")
    with pytest.raises(ValueError, match="invalid LOG_LEVEL"):
        logconf.setup("test")


def test_logging_supports_the_console_renderer(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("LOG_FORMAT", "console")
    logconf.setup("test")


def test_application_exception_handlers_return_closed_responses():
    request = SimpleNamespace(url=SimpleNamespace(path="/private"))
    payload = asyncio.run(main.client_payload_error(request, ClientPayloadError(413, "too large")))
    assert payload.status_code == 413
    assert payload.body == b'{"detail":"too large"}'

    unhandled = asyncio.run(main.unhandled(request, RuntimeError("private failure")))
    assert unhandled.status_code == 500
    assert unhandled.body == b'{"detail":"internal server error"}'

    saturated = asyncio.run(main.executor_saturated(request, ExecutorSaturatedError("full")))
    assert saturated.status_code == 429
    assert saturated.headers["retry-after"] == "1"
    assert saturated.body == b'{"detail":"Store upstream capacity reached"}'
