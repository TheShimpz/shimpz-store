"""Closed browser-visible chat event validation."""

from __future__ import annotations

import re

from fastapi import WebSocket, WebSocketDisconnect

from app.config import (
    MAX_CHAT_ASSISTANTS,
    MAX_CHAT_ERROR_DETAIL_CHARS,
    MAX_CHAT_FILES,
    MAX_CHAT_MESSAGE_CHARS,
    MAX_CHAT_REPLY_CHARS,
    MAX_WS_FRAME_BYTES,
)
from app.payloads import ClientPayloadError
from app.protocol.http.v1 import payload as team_contract
from app.protocol.http.v1 import websocket as chat_ws_common

_HUMAN_AUTH_KINDS = frozenset(
    {
        "auth:reauth",
        "auth:second-factor",
        "auth:phishing-resistant",
    }
)
_HUMAN_LENGTH_KINDS = {
    "input:text": 4096,
    "input:textarea": 16_000,
    "input:password": 1024,
    "input:phone": 64,
}
_HUMAN_SINGLE_CHOICE_KINDS = frozenset({"input:select", "input:choice"})
_HUMAN_BASE_FIELDS = frozenset(
    {"kind", "ordinal", "title", "description", "fingerprint"}
)


def canonical_chat_reply(value: object) -> str | None:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > MAX_CHAT_REPLY_CHARS
        or re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", value) is not None
    ):
        return None
    return value


def chat_turn_payload(payload: dict) -> dict[str, object]:
    """Project one browser turn onto the controller's closed Team chat contract."""
    if set(payload) != {"message", "files", "assistant_ids"}:
        raise ClientPayloadError(400, "body must contain only message, files, and assistant_ids")
    message = payload["message"]
    if not isinstance(message, str):
        raise ClientPayloadError(400, "message must be a string")
    message = message.strip()
    if not message:
        raise ClientPayloadError(400, "message must be non-empty")
    if len(message) > MAX_CHAT_MESSAGE_CHARS:
        raise ClientPayloadError(400, f"message too long (> {MAX_CHAT_MESSAGE_CHARS} chars)")
    files = payload["files"]
    if not isinstance(files, list) or len(files) > MAX_CHAT_FILES:
        raise ClientPayloadError(400, f"files must contain at most {MAX_CHAT_FILES} opaque ids")
    opaque_ids = [team_contract.canonical_file_id(file_id) for file_id in files]
    if any(file_id is None for file_id in opaque_ids) or len(opaque_ids) != len(set(opaque_ids)):
        raise ClientPayloadError(400, "files must contain unique opaque ids")
    assistant_ids = payload["assistant_ids"]
    if not isinstance(assistant_ids, list) or len(assistant_ids) > MAX_CHAT_ASSISTANTS:
        raise ClientPayloadError(
            400,
            f"assistant_ids must contain at most {MAX_CHAT_ASSISTANTS} Assistant ids",
        )
    canonical_ids = [team_contract.canonical_assistant_id(value) for value in assistant_ids]
    if any(value is None for value in canonical_ids) or len(canonical_ids) != len(set(canonical_ids)):
        raise ClientPayloadError(400, "assistant_ids must contain unique canonical Assistant ids")
    return {"message": message, "files": opaque_ids, "assistant_ids": canonical_ids}


WebSocketPayloadError = chat_ws_common.FrameError


async def ws_receive_bounded_json(ws: WebSocket) -> dict:
    message = await ws.receive()
    if message["type"] == "websocket.disconnect":
        raise WebSocketDisconnect(message.get("code", 1000))
    return chat_ws_common.decode_bounded_json_frame(
        message,
        MAX_WS_FRAME_BYTES,
        invalid_json_detail="WebSocket frame must be valid JSON",
    )


def _validated_done_event(value: dict, expected_team_id: str) -> dict | None:
    if set(value) != {"type", "team_id", "team_name", "reply"}:
        return None
    team_id = team_contract.canonical_team_id(value["team_id"])
    reply = canonical_chat_reply(value["reply"])
    team_name = team_contract.canonical_team_name(value["team_name"])
    if team_id is None or team_id != expected_team_id or reply is None or team_name is None:
        return None
    return {
        "type": "done",
        "team_id": team_id,
        "team_name": team_name,
        "reply": reply,
    }


def public_chat_error_event(status: int) -> dict:
    safe_status = chat_ws_common.safe_status(status)
    if safe_status == 429:
        detail = "chat service is busy; try again shortly"
    elif safe_status == 504:
        detail = "chat service timed out"
    elif safe_status < 500:
        detail = "chat request was rejected"
    else:
        detail = "chat service is temporarily unavailable"
    return {"type": "error", "status": safe_status, "detail": detail}


def _validated_error_event(value: dict) -> dict | None:
    if set(value) != {"type", "status", "detail"}:
        return None
    status = value["status"]
    detail = value["detail"]
    if (
        isinstance(status, bool)
        or not isinstance(status, int)
        or not 400 <= status <= 599
        or not isinstance(detail, str)
        or not detail
        or detail != detail.strip()
        or len(detail) > MAX_CHAT_ERROR_DETAIL_CHARS
        or re.search(r"[\x00-\x1f\x7f]", detail) is not None
    ):
        return None
    return public_chat_error_event(status)


def _public_text(value: object, maximum: int) -> str | None:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > maximum
        or not value.isprintable()
    ):
        return None
    return value


def _human_identity(value: object, label: str, maximum: int) -> dict[str, str] | None:
    if not isinstance(value, dict) or set(value) != {"id", label}:
        return None
    identifier = team_contract.canonical_assistant_id(value["id"])
    public_label = _public_text(value[label], maximum)
    if identifier is None or public_label is None:
        return None
    return {"id": identifier, label: public_label}


def _human_request_base(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    kind = value.get("kind")
    ordinal = value.get("ordinal")
    title = _public_text(value.get("title"), 80)
    description = _public_text(value.get("description"), 500)
    fingerprint = value.get("fingerprint")
    if (
        not isinstance(kind, str)
        or isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or not 0 <= ordinal < 8
        or title is None
        or description is None
        or not isinstance(fingerprint, str)
        or re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None
    ):
        return None
    return {
        "kind": kind,
        "ordinal": ordinal,
        "title": title,
        "description": description,
        "fingerprint": fingerprint,
    }


def _human_input_base(value: dict, base: dict[str, object]) -> dict[str, object] | None:
    label = _public_text(value.get("label"), 80)
    required = value.get("required")
    if label is None or not isinstance(required, bool):
        return None
    return {**base, "label": label, "required": required}


def _human_text_request(value: dict, base: dict[str, object], limit: int) -> dict | None:
    expected = _HUMAN_BASE_FIELDS | {"label", "required", "placeholder", "min_length", "max_length"}
    input_base = _human_input_base(value, base)
    placeholder = value.get("placeholder")
    minimum = value.get("min_length")
    maximum = value.get("max_length")
    if (
        set(value) != expected
        or input_base is None
        or (placeholder is not None and _public_text(placeholder, 120) is None)
        or isinstance(minimum, bool)
        or not isinstance(minimum, int)
        or isinstance(maximum, bool)
        or not isinstance(maximum, int)
        or not 0 <= minimum <= maximum <= limit
    ):
        return None
    return {
        **input_base,
        "placeholder": placeholder,
        "min_length": minimum,
        "max_length": maximum,
    }


def _human_options(value: object) -> list[dict[str, str | None]] | None:
    if not isinstance(value, list) or not 2 <= len(value) <= 32:
        return None
    options: list[dict[str, str | None]] = []
    for option in value:
        if not isinstance(option, dict) or set(option) != {"value", "label", "description"}:
            return None
        option_value = _public_text(option["value"], 128)
        label = _public_text(option["label"], 80)
        description = option["description"]
        if option_value is None or label is None or (
            description is not None and _public_text(description, 160) is None
        ):
            return None
        options.append({"value": option_value, "label": label, "description": description})
    if len({option["value"] for option in options}) != len(options):
        return None
    return options


def _human_choice_request(value: dict, base: dict[str, object], *, multiple: bool) -> dict | None:
    bounds = {"min_selections", "max_selections"} if multiple else set()
    expected = _HUMAN_BASE_FIELDS | {"label", "required", "options"} | bounds
    input_base = _human_input_base(value, base)
    options = _human_options(value.get("options"))
    if set(value) != expected or input_base is None or options is None:
        return None
    result = {**input_base, "options": options}
    if not multiple:
        return result
    minimum = value.get("min_selections")
    maximum = value.get("max_selections")
    if (
        isinstance(minimum, bool)
        or not isinstance(minimum, int)
        or isinstance(maximum, bool)
        or not isinstance(maximum, int)
        or not 0 <= minimum <= maximum <= len(options)
    ):
        return None
    return {**result, "min_selections": minimum, "max_selections": maximum}


def _human_request(value: object) -> dict | None:
    base = _human_request_base(value)
    if base is None or not isinstance(value, dict):
        return None
    kind = base["kind"]
    if kind == "approval" or kind in _HUMAN_AUTH_KINDS:
        return base if set(value) == _HUMAN_BASE_FIELDS else None
    if kind in _HUMAN_LENGTH_KINDS:
        return _human_text_request(value, base, _HUMAN_LENGTH_KINDS[kind])
    if kind in _HUMAN_SINGLE_CHOICE_KINDS:
        return _human_choice_request(value, base, multiple=False)
    if kind == "input:choices":
        return _human_choice_request(value, base, multiple=True)
    return None


def _validated_human_required_event(value: dict, expected_team_id: str) -> dict | None:
    expected = {
        "type",
        "status",
        "team_id",
        "turn_id",
        "challenge_id",
        "expires_in",
        "assistant",
        "power",
        "request",
    }
    identity = chat_ws_common.challenge_identity(value, expected_team_id)
    expires_in = value.get("expires_in")
    assistant = _human_identity(value.get("assistant"), "name", 80)
    power = _human_identity(value.get("power"), "summary", 160)
    request = _human_request(value.get("request"))
    if (
        set(value) != expected
        or value.get("type") != "human-required"
        or value.get("status") != "human-required"
        or identity is None
        or isinstance(expires_in, bool)
        or not isinstance(expires_in, int)
        or not 1 <= expires_in <= 300
        or assistant is None
        or power is None
        or request is None
    ):
        return None
    return {
        "type": "human-required",
        "challenge_id": identity[0],
        "expires_in": expires_in,
        "assistant": assistant,
        "power": power,
        "request": request,
    }


def validated_terminal_event(value: object, expected_team_id: str) -> dict | None:
    """Project an untrusted controller value onto the only browser-visible chat events."""
    if not isinstance(value, dict):
        return None
    event_type = value.get("type")
    terminal = None
    if event_type == "done":
        terminal = _validated_done_event(value, expected_team_id)
    elif event_type == "error":
        terminal = _validated_error_event(value)
    elif event_type == "stopped" and set(value) == {"type"}:
        terminal = {"type": "stopped"}
    elif event_type == "human-required":
        terminal = _validated_human_required_event(value, expected_team_id)
    return terminal


def parsed_stream_event(line: bytes, expected_team_id: str) -> dict | None:
    if not line.strip():
        return None
    try:
        event = chat_ws_common.decode_bounded_json_frame(
            {"type": "websocket.receive", "text": line.decode()},
            len(line),
        )
    except chat_ws_common.FrameError, UnicodeDecodeError:
        return None
    return validated_terminal_event(event, expected_team_id)


def upstream_error_event(status: int) -> dict:
    return public_chat_error_event(status)
