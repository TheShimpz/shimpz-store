"""Loopback Team chat stream and scripted browser WebSocket shared by the Store chat suites."""

import asyncio
import contextlib
from http.server import BaseHTTPRequestHandler

from starlette.websockets import WebSocket

from app import config
from app.chat import ws
from tests.loopback import PeerMixin, loopback_server


TEST_TEAM_ID = "test_team"


def done_event(
    reply: str = "hello",
    *,
    team_id: str = TEST_TEAM_ID,
    team_name: str = "Marketing",
    clarification: dict | None = None,
) -> dict:
    """Return one Team terminal ``done`` event for the Store relay suites."""
    return {
        "type": "done",
        "team_id": team_id,
        "team_name": team_name,
        "reply": reply,
        "clarification": clarification,
    }


@contextlib.contextmanager
def real_stream_team(response_body: bytes, *, status: int = 200):
    requests: list[bytes] = []

    class Handler(PeerMixin, BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            requests.append(self.rfile.read(length))
            self.send_response(status)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)

    with loopback_server(Handler) as port:
        previous = config.TEAM_URL
        config.TEAM_URL = f"http://127.0.0.1:{port}"
        try:
            yield requests
        finally:
            config.TEAM_URL = previous


async def run_admitted_turn(websocket, team_id: str, message: str, started: asyncio.Event) -> None:
    """Relay one chat turn through the live admitted entrypoint, as an accepted WebSocket chat frame does."""
    lease = ws._TURN_ADMISSION.reserve()
    assert lease is not None
    turn = ws._WsTurn(
        ws=websocket, team_id=team_id, headers={}, text=message, started=started, dispatched=asyncio.Event()
    )
    await ws._ws_run_admitted_turn(turn, lease)


def scripted_websocket(text: str) -> tuple[WebSocket, list[dict]]:
    """Return a WebSocket that connects, receives one text frame, and records every message Store sends."""
    incoming = iter(
        (
            {"type": "websocket.connect"},
            {"type": "websocket.receive", "text": text},
        )
    )

    async def receive() -> dict:
        return next(incoming)

    sent = []

    async def send(message: dict) -> None:
        sent.append(message)

    return WebSocket({"type": "websocket", "path": "/"}, receive, send), sent
