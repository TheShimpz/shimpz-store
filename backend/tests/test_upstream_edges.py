"""Edge coverage for bounded Store upstream transports."""

from __future__ import annotations

import asyncio

import pytest

from app import upstream


class _Response:
    def __init__(self, status=200, body=b"", headers=None):
        self.status = status
        self.body = body
        self.headers = headers or {}

    def read(self, maximum):
        return self.body[:maximum]

    def getheader(self, name):
        return self.headers.get(name)


class _Connection:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.closed = False
        self.requests = []

    def request(self, *args, **kwargs):
        self.requests.append((args, kwargs))
        if self.error is not None:
            raise self.error

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


def _install(monkeypatch, connection):
    monkeypatch.setattr(upstream.http.client, "HTTPConnection", lambda *_args, **_kwargs: connection)


def test_json_transport_rejects_an_oversized_response(monkeypatch):
    connection = _Connection(_Response(body=b"{}x"))
    _install(monkeypatch, connection)
    assert upstream.call("http://service:80", "GET", "/", timeout=1, max_response_bytes=2) == (
        502,
        {"detail": "the Space returned an oversized response"},
    )
    assert connection.closed


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (_Response(status=404, body=b"ignored"), (404, b"")),
        (_Response(headers={"Content-Type": "text/plain", "Content-Length": "1"}), (502, b"")),
        (_Response(headers={"Content-Type": "image/png", "Content-Length": "bad"}), (502, b"")),
        (_Response(headers={"Content-Type": "image/png", "Content-Length": "0"}), (502, b"")),
        (
            _Response(body=b"png", headers={"Content-Type": "image/png; charset=binary", "Content-Length": "3"}),
            (200, b"png"),
        ),
        (_Response(body=b"short", headers={"Content-Type": "image/png", "Content-Length": "6"}), (502, b"")),
    ],
)
def test_asset_transport_enforces_status_type_length_and_exact_body(monkeypatch, response, expected):
    connection = _Connection(response)
    _install(monkeypatch, connection)
    assert upstream.call_asset("http://developers:8080", "/icon.png", timeout=1) == expected
    assert connection.closed


def test_asset_transport_closes_on_network_failure(monkeypatch):
    connection = _Connection(error=OSError("unreachable"))
    _install(monkeypatch, connection)
    assert upstream.call_asset("http://developers:8080", "/icon.png", timeout=1) == (502, b"")
    assert connection.closed


def test_asset_bounded_delegates_to_the_caller_executor(monkeypatch):
    captured = []

    async def run(executor, operation):
        captured.append(executor)
        return operation()

    monkeypatch.setattr(upstream, "run_bounded", run)
    monkeypatch.setattr(upstream, "call_asset", lambda *_args, **_kwargs: (200, b"asset"))
    executor = object()
    assert asyncio.run(
        upstream.call_asset_bounded(executor, "http://developers:8080", "/icon.png", timeout=1)
    ) == (200, b"asset")
    assert captured == [executor]
