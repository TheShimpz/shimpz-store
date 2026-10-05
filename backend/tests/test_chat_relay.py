import asyncio
import contextlib
import http.client
import json
import threading
from http.server import BaseHTTPRequestHandler

import pytest

from app import config
from app.chat.relay import _relay_upstream_events
from app.chat import ws as main
from tests.chat_relay_fixture import real_stream_team as _real_stream_team
from tests.chat_relay_fixture import run_admitted_turn
from tests.chat_relay_fixture import scripted_websocket as _websocket
from tests.loopback import loopback_server

TEST_TEAM_ID = "test_team"


def _done(
    reply: str = "hello",
    *,
    team_id: str = TEST_TEAM_ID,
    team_name: str = "Marketing",
    clarification: dict | None = None,
) -> dict:
    return {
        "type": "done",
        "team_id": team_id,
        "team_name": team_name,
        "reply": reply,
        "clarification": clarification,
    }


@contextlib.contextmanager
def _real_upstream(body: bytes):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args) -> None:
            pass

    with loopback_server(Handler) as port:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        try:
            connection.request("GET", "/stream")
            yield connection.getresponse()
        finally:
            connection.close()


def _relay(body: bytes, team_id: str = TEST_TEAM_ID) -> dict:
    async def scenario() -> dict:
        with _real_upstream(body) as response:
            return await asyncio.to_thread(_relay_upstream_events, response, team_id)

    return asyncio.run(scenario())


@contextlib.contextmanager
def _real_delayed_upstream(first: bytes, rest: bytes):
    first_flushed = threading.Event()
    release_rest = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            body_size = len(first) + len(rest)
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Content-Length", str(body_size))
            self.end_headers()
            self.wfile.write(first)
            self.wfile.flush()
            first_flushed.set()
            if release_rest.wait(timeout=5):
                self.wfile.write(rest)
                self.wfile.flush()

        def log_message(self, *_args) -> None:
            pass

    with loopback_server(Handler) as port:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        try:
            connection.request("GET", "/stream")
            yield connection.getresponse(), first_flushed, release_rest
        finally:
            release_rest.set()
            connection.close()


def test_upstream_relay_releases_nothing_before_one_complete_terminal_event():
    async def scenario() -> None:
        first = b'{"type":"done","team_id":"test_team",'
        rest = b'"team_name":"Marketing","reply":"first","clarification":null}\n'
        with _real_delayed_upstream(first, rest) as (
            response,
            first_flushed,
            release_rest,
        ):
            relay = asyncio.create_task(
                asyncio.to_thread(
                    _relay_upstream_events,
                    response,
                    TEST_TEAM_ID,
                )
            )
            assert await asyncio.to_thread(first_flushed.wait, 1)
            assert not relay.done()
            release_rest.set()
            assert await asyncio.wait_for(relay, timeout=2) == _done("first")

    asyncio.run(scenario())


def test_stream_transport_preserves_utf8_prompt_and_reply_bytes():
    async def scenario() -> None:
        reply = "Olá, Capitão 🦐"
        encoded_reply = (
            json.dumps(
                _done(reply, team_id="team_utf8"),
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode()
            + b"\n"
        )
        loop = asyncio.get_running_loop()
        started = asyncio.Event()
        prompt = "ação e camarão 🦐"
        opaque_file = "a" * 32
        with _real_stream_team(encoded_reply) as requests:
            event = await asyncio.to_thread(
                main._stream_lines,
                main._StreamRelay(
                    "team_utf8",
                    prompt,
                    {},
                    loop,
                    started,
                    (opaque_file,),
                    ("shimpz-cloudflare",),
                ),
            )
        await asyncio.wait_for(started.wait(), timeout=1)
        assert len(requests) == 1
        assert json.loads(requests[0]) == {
            "message": prompt,
            "files": [opaque_file],
            "assistant_ids": ["shimpz-cloudflare"],
            "conversation": [],
            "locale": None,
        }
        assert prompt.encode() in requests[0]
        assert b"\\u" not in requests[0]
        assert event == _done(reply, team_id="team_utf8")

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "terminal",
    [
        pytest.param(
            {
                "type": "error",
                "status": 504,
                "detail": "the brain did not answer within 170s",
            },
            id="rc-124-timeout",
        ),
        pytest.param(
            {"type": "error", "status": 500, "detail": "brain error (rc=23)"},
            id="nonzero-rc",
        ),
        pytest.param(
            {
                "type": "error",
                "status": 502,
                "detail": "brain stream ended without a completion event",
            },
            id="missing-completion",
        ),
    ],
)
def test_team_terminal_failures_reach_websocket_as_errors(terminal: dict):
    async def scenario() -> None:
        websocket, sent = _websocket("{}")
        await websocket.accept()
        started = asyncio.Event()
        response = json.dumps(terminal, separators=(",", ":")).encode() + b"\n"
        with _real_stream_team(response) as requests:
            await run_admitted_turn(websocket, "team-terminal", "hello", started)
        events = [json.loads(message["text"]) for message in sent if message["type"] == "websocket.send"]
        assert started.is_set()
        assert len(requests) == 1
        expected_detail = (
            "chat service timed out" if terminal["status"] == 504 else "chat service is temporarily unavailable"
        )
        assert events == [
            {
                "type": "error",
                "status": terminal["status"],
                "detail": expected_detail,
            }
        ]
        assert all(event.get("type") == "error" for event in events)
        assert not any(event.get("type") == "done" for event in events)

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("status", "payload"),
    [
        (409, {"error": "team already has an active chat turn"}),
        (429, {"detail": "chat rate limit exceeded"}),
    ],
)
def test_real_upstream_non_2xx_reaches_websocket_redacted(status: int, payload: dict):
    async def scenario() -> None:
        websocket, sent = _websocket("{}")
        await websocket.accept()
        started = asyncio.Event()
        body = json.dumps(payload, separators=(",", ":")).encode()
        with _real_stream_team(body, status=status) as requests:
            await run_admitted_turn(websocket, "team-upstream-error", "hello", started)
        events = [json.loads(message["text"]) for message in sent if message["type"] == "websocket.send"]
        assert started.is_set()
        assert len(requests) == 1
        assert events == [
            {
                "type": "error",
                "status": status,
                "detail": ("chat service is busy; try again shortly" if status == 429 else "chat request was rejected"),
            }
        ]

    asyncio.run(scenario())


def test_upstream_relay_is_bounded_and_fails_closed_on_protocol_errors():
    success = json.dumps(_done(), separators=(",", ":")).encode()
    assert _relay(success) == _done()

    protocol_error = {
        "type": "error",
        "status": 502,
        "detail": "team stream violated the terminal event contract",
        "_relay_abort": True,
    }
    text_then_terminal = b'{"type":"text","text":"partial"}\n' + json.dumps(_done()).encode() + b"\n"
    assert _relay(text_then_terminal) == protocol_error

    malformed = b"not-json\n" + json.dumps(_done()).encode() + b"\n"
    assert _relay(malformed) == protocol_error

    extra_after_terminal = json.dumps(_done()).encode() + b'\n{"type":"stopped"}\n'
    assert _relay(extra_after_terminal) == protocol_error

    mismatched_team = json.dumps(_done(team_id="another_team")).encode() + b"\n"
    assert _relay(mismatched_team) == protocol_error

    asked = {
        "question": "Qual período?",
        "options": [{"label": "Hoje", "description": ""}, {"label": "Semana", "description": "Sete dias."}],
        "default_index": 0,
    }
    rendered = "Qual período?\n\n1. Hoje ✓\n2. Semana — Sete dias."
    clarified = json.dumps(_done(rendered, clarification=asked)).encode() + b"\n"
    assert _relay(clarified) == _done(rendered, clarification=asked)
    unrelated_reply = json.dumps(_done("I deleted everything.", clarification=asked)).encode() + b"\n"
    assert _relay(unrelated_reply) == protocol_error
    malformed_question = json.dumps(_done(rendered, clarification={**asked, "default_index": 5})).encode() + b"\n"
    assert _relay(malformed_question) == protocol_error
    missing_field = {key: value for key, value in _done().items() if key != "clarification"}
    assert _relay(json.dumps(missing_field).encode() + b"\n") == protocol_error

    assert _relay(b"") == protocol_error

    oversized = b"x" * (config.MAX_UPSTREAM_STREAM_LINE_BYTES + 1)
    assert _relay(oversized) == protocol_error
