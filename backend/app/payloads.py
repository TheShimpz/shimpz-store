"""Bounded duplicate-safe JSON request parsing."""

from __future__ import annotations

import json

from fastapi import Request

from app import chat_ws_common


class ClientPayloadError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


unique_json_object = chat_ws_common.unique_json_object


async def read_bounded_json(request: Request, max_bytes: int) -> dict:
    """Read one JSON object without ever buffering more than `max_bytes`."""
    raw_length = request.headers.get("content-length")
    if raw_length:
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ClientPayloadError(400, "invalid Content-Length") from exc
        if length < 0:
            raise ClientPayloadError(400, "invalid Content-Length")
        if length > max_bytes:
            raise ClientPayloadError(413, f"request body too large (max {max_bytes} bytes)")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > max_bytes:
            raise ClientPayloadError(413, f"request body too large (max {max_bytes} bytes)")
        body.extend(chunk)
    try:
        payload = json.loads(body or b"{}", object_pairs_hook=unique_json_object)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ClientPayloadError(400, "invalid JSON body") from exc
    if not isinstance(payload, dict):
        raise ClientPayloadError(400, "JSON body must be an object")
    return payload
