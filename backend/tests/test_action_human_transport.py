import asyncio
import json

import pytest
from fastapi import WebSocket

from app.chat import ws as main
from app.chat.events import validated_terminal_event as _validated_terminal_event
from app.chat.ws import _ws_dispatch

TEST_TEAM_ID = "test_team"


def _done(reply: str = "hello") -> dict:
    return {
        "type": "done",
        "team_id": TEST_TEAM_ID,
        "team_name": "Marketing",
        "reply": reply,
    }


def _human_request(kind: str, **fields: object) -> dict:
    return {
        "kind": kind,
        "ordinal": 0,
        "title": "Provide reviewed input",
        "description": "Provide only the information requested by this exact Action.",
        "fingerprint": "d" * 64,
        **fields,
    }


def _human_challenge(
    *,
    team_id: str = TEST_TEAM_ID,
    challenge_id: str = "c" * 32,
    request: dict | None = None,
) -> dict:
    return {
        "type": "human-required",
        "status": "human-required",
        "team_id": team_id,
        "turn_id": challenge_id,
        "challenge_id": challenge_id,
        "expires_in": 300,
        "assistant": {"id": "shimpz-cloudflare", "name": "Shimpz Cloudflare", "version": "0.4.1"},
        "action": {"id": "list-zones", "summary": "List reviewed Cloudflare zones."},
        "request": request or _human_request("approval"),
    }


def _websocket(text: str) -> tuple[WebSocket, list[dict]]:
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


def test_websocket_blocks_new_turn_until_pending_human_challenge_is_resolved():
    async def scenario() -> None:
        websocket, sent = _websocket("{}")
        await websocket.accept()
        await _ws_dispatch(
            websocket,
            TEST_TEAM_ID,
            {},
            {"type": "chat", "message": "next", "files": [], "assistant_ids": []},
            {
                "active": None,
                "pending_human": {
                    "challenge_id": "c" * 32,
                    "request": _human_request("approval"),
                },
            },
        )
        assert json.loads(sent[-1]["text"]) == {
            "type": "error",
            "status": 409,
            "detail": "a human challenge must be resolved before another turn",
        }

    asyncio.run(scenario())


def test_websocket_auth_response_accepts_only_one_use_account_handle():
    async def scenario() -> None:
        websocket, sent = _websocket("{}")
        await websocket.accept()
        state = {
            "active": None,
            "pending_human": {
                "challenge_id": "c" * 32,
                "request": _human_request("auth:password"),
            },
        }
        await _ws_dispatch(
            websocket,
            TEST_TEAM_ID,
            {},
            {
                "type": "human-response",
                "challenge_id": "c" * 32,
                "decision": "submit",
                "value": "raw-account-password",
            },
            state,
        )
        assert json.loads(sent[-1]["text"]) == {
            "type": "error",
            "status": 400,
            "detail": "authentication response must be a one-use assurance handle",
        }
        assert state["pending_human"] is not None

    asyncio.run(scenario())


def test_websocket_submits_exact_human_response_without_browser_type(monkeypatch):
    async def scenario() -> None:
        captured = []

        def start(context, response, lease):
            captured.append((context, response))
            task = asyncio.create_task(asyncio.sleep(0))
            return task, asyncio.Event(), asyncio.Event(), main._RelayDelivery()

        monkeypatch.setattr(main, "_start_ws_human", start)
        websocket, _ = _websocket("{}")
        await websocket.accept()
        state = {
            "active": None,
            "pending_human": {
                "challenge_id": "c" * 32,
                "request": _human_request("auth:totp"),
            },
        }
        await _ws_dispatch(
            websocket,
            TEST_TEAM_ID,
            {"X-Shimpz-Account": "session"},
            {
                "type": "human-response",
                "challenge_id": "c" * 32,
                "decision": "submit",
                "value": "a" * 43,
            },
            state,
        )
        await asyncio.sleep(0)
        assert captured[0][1] == {
            "challenge_id": "c" * 32,
            "decision": "submit",
            "value": "a" * 43,
        }
        assert state["pending_human"] is None

    asyncio.run(scenario())


def test_final_websocket_gate_remembers_only_public_human_challenge():
    async def scenario() -> None:
        websocket, sent = _websocket("{}")
        await websocket.accept()
        state = {"pending_human": None}
        turn = main._WsTurn(
            websocket,
            TEST_TEAM_ID,
            {"X-Shimpz-Account": "session"},
            "hello",
            asyncio.Event(),
            asyncio.Event(),
            state=state,
        )
        await main._send_relay_event(turn, _human_challenge(), main._RelayDelivery())
        assert json.loads(sent[-1]["text"]) == _validated_terminal_event(
            _human_challenge(),
            TEST_TEAM_ID,
        )
        assert state["pending_human"] == {
            "challenge_id": "c" * 32,
            "request": _human_request("approval"),
        }

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (
            200,
            {"team_id": TEST_TEAM_ID, "team_name": "Marketing", "reply": "done"},
            _done("done"),
        ),
        (
            200,
            {"team_id": TEST_TEAM_ID, "status": "human-denied", "reason": "denied"},
            {"type": "stopped"},
        ),
        (
            200,
            {
                "team_id": TEST_TEAM_ID,
                "status": "human-denied",
                "reason": "authentication-failed",
            },
            {"type": "error", "status": 403, "detail": "authentication was not confirmed"},
        ),
        (
            428,
            {key: value for key, value in _human_challenge().items() if key != "type"},
            _human_challenge(),
        ),
    ],
)
def test_hosted_human_resume_maps_only_current_team_terminals(
    monkeypatch,
    status: int,
    body: dict,
    expected: dict,
):
    monkeypatch.setattr(main, "_call", lambda *_args, **_kwargs: (status, body))

    async def scenario() -> None:
        started = asyncio.Event()
        result = main._resume_human(
            TEST_TEAM_ID,
            {"X-Shimpz-Account": "session"},
            {"challenge_id": "c" * 32, "decision": "deny"},
            asyncio.get_running_loop(),
            started,
        )
        await asyncio.sleep(0)
        assert started.is_set()
        assert result == expected

    asyncio.run(scenario())


def test_terminal_event_contract_projects_exact_public_human_challenge():
    expected = {
        "type": "human-required",
        "challenge_id": "c" * 32,
        "expires_in": 300,
        "assistant": {"id": "shimpz-cloudflare", "name": "Shimpz Cloudflare", "version": "0.4.1"},
        "action": {"id": "list-zones", "summary": "List reviewed Cloudflare zones."},
        "request": _human_request("approval"),
    }

    assert _validated_terminal_event(_human_challenge(), TEST_TEAM_ID) == expected


@pytest.mark.parametrize(
    "descriptor",
    [
        _human_request("approval"),
        _human_request("auth:password"),
        _human_request("auth:totp"),
        _human_request("auth:passkey"),
        *[
            _human_request(
                kind,
                label="Requested value",
                required=True,
                placeholder=None,
                min_length=1,
                max_length=maximum,
            )
            for kind, maximum in (
                ("input:text", 4096),
                ("input:textarea", 16_000),
                ("input:password", 1024),
                ("input:phone", 64),
            )
        ],
        *[
            _human_request(
                kind,
                label="Requested option",
                required=True,
                options=[
                    {"value": "one", "label": "One", "description": None},
                    {"value": "two", "label": "Two", "description": "Second option"},
                ],
            )
            for kind in ("input:select", "input:choice")
        ],
        _human_request(
            "input:choices",
            label="Requested options",
            required=True,
            options=[
                {"value": "one", "label": "One", "description": None},
                {"value": "two", "label": "Two", "description": "Second option"},
            ],
            min_selections=1,
            max_selections=2,
        ),
    ],
)
def test_terminal_event_contract_projects_every_reviewed_human_request(descriptor: dict):
    event = _human_challenge(request=descriptor)

    projected = _validated_terminal_event(event, TEST_TEAM_ID)

    assert projected is not None
    assert projected["request"] == descriptor


@pytest.mark.parametrize(
    "event",
    [
        {**_human_challenge(), "private": "must-not-cross"},
        _human_challenge(team_id="other_team"),
        {**_human_challenge(), "turn_id": "e" * 32},
        {**_human_challenge(), "expires_in": 301},
        {
            **_human_challenge(),
            "request": {**_human_challenge()["request"], "kind": "unreviewed"},
        },
        {
            **_human_challenge(),
            "request": {**_human_challenge()["request"], "secret": "must-not-cross"},
        },
    ],
)
def test_terminal_event_contract_rejects_unreviewed_human_values(event: dict):
    assert _validated_terminal_event(event, TEST_TEAM_ID) is None
