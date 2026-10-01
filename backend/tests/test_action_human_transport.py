import asyncio
import hashlib
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


PACK_DIGEST = "sha256:" + "5" * 64
COPY_FIELDS = ("title", "description", "label", "placeholder")


def _reference(text: str, **params: object) -> dict:
    """A catalog reference whose message id is the SHA-256 of the English template (ADR-0091)."""
    return {"message": hashlib.sha256(text.encode()).hexdigest(), "params": params}


def _human_request(kind: str, **fields: object) -> dict:
    """A canonical request whose plain-copy fields become catalog references."""
    copy = {
        field: None if fields[field] is None else _reference(fields[field])
        for field in ("label", "placeholder")
        if field in fields
    }
    options = (
        {
            "options": [
                {
                    "value": option["value"],
                    "label": _reference(option["label"]),
                    "description": None if option["description"] is None else _reference(option["description"]),
                }
                for option in fields["options"]
            ]
        }
        if "options" in fields
        else {}
    )
    return {
        "kind": kind,
        "ordinal": 0,
        "title": _reference("Provide reviewed input"),
        "description": _reference("Provide only the information requested by this exact Action."),
        "fingerprint": "d" * 64,
        **fields,
        **copy,
        **options,
    }


def _rendered(request: dict) -> dict:
    """Display copy for exactly the request's copy fields, null only where the reference is null."""
    rendered: dict = {
        field: None if request[field] is None else f"Rendered {field}" for field in COPY_FIELDS if field in request
    }
    if "options" in request:
        rendered["options"] = [
            {
                "label": f"Option {index}",
                "description": None if option["description"] is None else f"Description {index}",
            }
            for index, option in enumerate(request["options"])
        ]
    return rendered


def _human_challenge(
    *,
    team_id: str = TEST_TEAM_ID,
    challenge_id: str = "c" * 32,
    request: dict | None = None,
) -> dict:
    request = request or _human_request("approval")
    return {
        "type": "human-required",
        "status": "human-required",
        "team_id": team_id,
        "turn_id": challenge_id,
        "challenge_id": challenge_id,
        "expires_in": 300,
        "assistant": {"id": "shimpz-cloudflare", "name": "Shimpz Cloudflare", "version": "0.4.1"},
        "action": {"id": "list-zones", "summary": "List reviewed Cloudflare zones."},
        "request": request,
        "rendered": _rendered(request),
        "locale": "en",
        "pack_digest": PACK_DIGEST,
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
        "rendered": {"title": "Rendered title", "description": "Rendered description"},
        "locale": "en",
        "pack_digest": PACK_DIGEST,
    }

    assert _validated_terminal_event(_human_challenge(), TEST_TEAM_ID) == expected


def test_terminal_event_contract_projects_the_brain_purpose_beside_the_request():
    purpose = "To publish the DNS change you asked for, I need Cloudflare."
    projected = _validated_terminal_event({**_human_challenge(), "purpose": purpose}, TEST_TEAM_ID)

    assert projected is not None
    assert projected["purpose"] == purpose
    assert projected["request"] == _human_request("approval")


KEY_PAGE = "https://dash.cloudflare.com/profile/api-tokens"


def _stored_input_request(stored_input: str = "cloudflare-token") -> dict:
    return _human_request(
        "input:password",
        label="Cloudflare API token",
        required=True,
        placeholder=None,
        min_length=1,
        max_length=1024,
        stored_input=stored_input,
    )


def test_hosted_relay_forwards_a_stored_input_request_with_its_key_page_and_purpose():
    purpose = "To publish the DNS change you asked for, I need Cloudflare."

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
        challenge = {**_human_challenge(request=_stored_input_request()), "purpose": purpose, "help_url": KEY_PAGE}
        await main._send_relay_event(turn, challenge, main._RelayDelivery())
        relayed = json.loads(sent[-1]["text"])
        assert relayed["request"] == _stored_input_request()
        assert (relayed["purpose"], relayed["help_url"]) == (purpose, KEY_PAGE)
        assert state["pending_human"] == {"challenge_id": "c" * 32, "request": _stored_input_request()}

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "event",
    [
        {**_human_challenge(), "purpose": "Search \u2014 then publish"},
        {**_human_challenge(), "purpose": None},
        {**_human_challenge(), "help_url": KEY_PAGE},
        {**_human_challenge(request=_stored_input_request()), "help_url": "http://dash.cloudflare.com/x"},
        {**_human_challenge(request=_stored_input_request()), "help_url": KEY_PAGE + "\n"},
        _human_challenge(request=_stored_input_request(stored_input="Not An Id")),
        _human_challenge(
            request=_human_request(
                "input:text",
                label="Zone",
                required=True,
                placeholder=None,
                min_length=1,
                max_length=64,
                stored_input="cloudflare-token",
            )
        ),
    ],
)
def test_terminal_event_contract_refuses_invalid_presentation_or_misplaced_stored_input(event: dict):
    assert _validated_terminal_event(event, TEST_TEAM_ID) is None


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


def _portuguese_choice() -> dict:
    request = _human_request(
        "input:choice",
        label="Mode",
        required=True,
        options=[
            {"value": "proxied", "label": "Proxied", "description": "Route traffic through Cloudflare."},
            {"value": "dns-only", "label": "DNS only", "description": None},
        ],
    )
    return {
        **_human_challenge(request=request),
        "rendered": {
            "title": "Forneça a entrada revisada",
            "description": "Forneça apenas o que esta Ação exata pede.",
            "label": "Modo",
            "options": [
                {"label": "Com proxy", "description": "Encaminhar o tráfego pela Cloudflare."},
                {"label": "Somente DNS", "description": None},
            ],
        },
        "locale": "pt",
    }


def test_hosted_relay_forwards_the_rendered_copy_locale_and_pack_beside_the_canonical_request():
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
        challenge = _portuguese_choice()
        await main._send_relay_event(turn, challenge, main._RelayDelivery())
        relayed = json.loads(sent[-1]["text"])
        assert relayed["request"] == challenge["request"]
        assert relayed["rendered"] == challenge["rendered"]
        assert (relayed["locale"], relayed["pack_digest"]) == ("pt", PACK_DIGEST)
        assert [option["value"] for option in relayed["request"]["options"]] == ["proxied", "dns-only"]
        # Only the canonical request is kept to check the answer; display copy never decides what is admitted.
        assert state["pending_human"] == {"challenge_id": "c" * 32, "request": challenge["request"]}

    asyncio.run(scenario())


def _without(name: str) -> dict:
    return {key: value for key, value in _portuguese_choice().items() if key != name}


def _rendered_with(**change: object) -> dict:
    challenge = _portuguese_choice()
    return {**challenge, "rendered": {**challenge["rendered"], **change}}


_FIRST, _SECOND = _portuguese_choice()["rendered"]["options"]


@pytest.mark.parametrize(
    "event",
    [
        _without("rendered"),
        _without("locale"),
        _without("pack_digest"),
        {**_portuguese_choice(), "locale": None},
        {**_portuguese_choice(), "locale": "pt-BR"},
        {**_portuguese_choice(), "pack_digest": "sha256:" + "A" * 64},
        {**_portuguese_choice(), "pack_digest": "5" * 64},
        {**_portuguese_choice(), "rendered": None},
        _rendered_with(placeholder=None),
        _rendered_with(title="x" * 81),
        _rendered_with(title=" Forneça"),
        _rendered_with(description="Café"),
        _rendered_with(options=[_FIRST]),
        _rendered_with(options=[_FIRST, {"label": "Somente DNS", "description": "x"}]),
        _rendered_with(options=[{**_FIRST, "value": "proxied"}, _SECOND]),
        {**_portuguese_choice(), "request": {**_portuguese_choice()["request"], "title": "Provide reviewed input"}},
    ],
)
def test_terminal_event_contract_refuses_a_challenge_without_exactly_its_localized_copy(event: dict):
    assert _validated_terminal_event(event, TEST_TEAM_ID) is None
