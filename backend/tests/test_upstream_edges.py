"""Edge coverage for bounded Store upstream transports."""

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
    monkeypatch.setattr(upstream, "MAX_JSON_RESPONSE_BYTES", 2)
    assert upstream.call("/") == (
        502,
        {"detail": "the upstream returned an oversized response"},
    )
    assert connection.closed


@pytest.mark.parametrize(("body", "expected"), [(b'{"version":1}', {"version": 1}), (b"", {})])
def test_json_transport_returns_the_status_and_decoded_body(monkeypatch, body, expected):
    connection = _Connection(_Response(status=200, body=body))
    _install(monkeypatch, connection)
    assert upstream.call("/api/v1/assistants") == (200, expected)
    assert connection.requests == [(("GET", "/api/v1/assistants"), {})]
    assert connection.closed


def test_json_transport_closes_on_network_failure(monkeypatch):
    connection = _Connection(error=OSError("unreachable"))
    _install(monkeypatch, connection)
    assert upstream.call("/") == (
        502,
        {"detail": "the upstream is unreachable"},
    )
    assert connection.closed


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (_Response(status=404, body=b"ignored"), (404, b"")),
        (_Response(headers={"Content-Type": "text/plain", "Content-Length": "1"}), (502, b"")),
        (_Response(headers={"Content-Type": "image/png", "Content-Length": "bad"}), (502, b"")),
        (_Response(headers={"Content-Type": "image/png", "Content-Length": "0"}), (502, b"")),
        (_Response(body=b"png", headers={"Content-Type": "image/png", "Content-Length": "+3"}), (502, b"")),
        (_Response(body=b"png", headers={"Content-Type": "image/png", "Content-Length": " 3"}), (502, b"")),
        (_Response(body=b"p" * 10, headers={"Content-Type": "image/png", "Content-Length": "1_0"}), (502, b"")),
        (_Response(body=b"png", headers={"Content-Type": "image/png", "Content-Length": "\u0663"}), (502, b"")),
        (_Response(body=b"png", headers={"Content-Type": "image/png", "Content-Length": ""}), (502, b"")),
        (_Response(body=b"png", headers={"Content-Type": "image/png", "Content-Length": "9" * 5000}), (502, b"")),
        (_Response(body=b"png", headers={"Content-Type": "image/png", "Content-Length": "00000003"}), (502, b"")),
        (_Response(body=b"png", headers={"Content-Type": "image/png", "Content-Length": "0000003"}), (200, b"png")),
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
    assert upstream.call_asset("/icon.png") == expected
    assert connection.closed


def test_asset_transport_closes_on_network_failure(monkeypatch):
    connection = _Connection(error=OSError("unreachable"))
    _install(monkeypatch, connection)
    assert upstream.call_asset("/icon.png") == (502, b"")
    assert connection.closed


@pytest.mark.parametrize(
    "body",
    [
        b'{"version":1,"version":1}',
        b'{"version":NaN}',
        b'{"version":1e999}',
        b'\xef\xbb\xbf{"version":1}',
        b'{"name":"\\ud800"}',
        b'{"name":"\xff"}',
        b"[" * 600 + b"]" * 600,
        b"HTTP/1.1 PRIVATE_SENTINEL",
    ],
)
def test_json_transport_refuses_what_strict_json_refuses(monkeypatch, body):
    connection = _Connection(_Response(status=200, body=body))
    _install(monkeypatch, connection)
    assert upstream.call("/api/v1/assistants") == (502, {"detail": "the upstream is unreachable"})
    assert connection.closed


def test_upstream_failures_log_only_closed_codes(monkeypatch, capsys):
    """A Developers status line or socket error text never reaches a log line, only the failure's class."""
    connection = _Connection(error=upstream.http.client.BadStatusLine("PRIVATE_SENTINEL"))
    _install(monkeypatch, connection)
    assert upstream.call("/api/v1/assistants?locale=en")[0] == 502
    assert upstream.call_asset("/icon.png") == (502, b"")

    rendered = capsys.readouterr().out
    assert "PRIVATE_SENTINEL" not in rendered
    assert rendered.count('"error": "BadStatusLine"') == 2
