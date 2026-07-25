"""Closed browser-visible chat event validation."""

from __future__ import annotations

import re

from fastapi import WebSocket, WebSocketDisconnect

from app import chat_ws_common, team_driver_contract
from app.config import (
    MAX_CHAT_ASSISTANTS,
    MAX_CHAT_ERROR_DETAIL_CHARS,
    MAX_CHAT_FILES,
    MAX_CHAT_MESSAGE_CHARS,
    MAX_CHAT_REPLY_CHARS,
    MAX_WS_FRAME_BYTES,
)
from app.payloads import ClientPayloadError


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
    opaque_ids = [team_driver_contract.canonical_file_id(file_id) for file_id in files]
    if any(file_id is None for file_id in opaque_ids) or len(opaque_ids) != len(set(opaque_ids)):
        raise ClientPayloadError(400, "files must contain unique opaque ids")
    assistant_ids = payload["assistant_ids"]
    if not isinstance(assistant_ids, list) or len(assistant_ids) > MAX_CHAT_ASSISTANTS:
        raise ClientPayloadError(
            400,
            f"assistant_ids must contain at most {MAX_CHAT_ASSISTANTS} Assistant ids",
        )
    canonical_ids = [team_driver_contract.canonical_assistant_id(value) for value in assistant_ids]
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
    team_id = team_driver_contract.canonical_team_id(value["team_id"])
    reply = canonical_chat_reply(value["reply"])
    team_name = team_driver_contract.canonical_team_name(value["team_name"])
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
