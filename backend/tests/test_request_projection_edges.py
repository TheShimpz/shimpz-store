"""Fail-closed request parsing and controller projection edge coverage."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import Request

from app import projections
from app.config import MAX_CHAT_ASSISTANTS
from app.payloads import ClientPayloadError, read_bounded_json


def _request(body: bytes, headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    delivered = False

    async def receive() -> dict[str, object]:
        nonlocal delivered
        if delivered:
            return {"type": "http.disconnect"}
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request({"type": "http", "headers": headers or []}, receive)


@pytest.mark.parametrize(
    ("body", "headers", "detail"),
    [
        (b"{}", [(b"content-length", b"invalid")], "invalid Content-Length"),
        (b"{}", [(b"content-length", b"-1")], "invalid Content-Length"),
        (b'{"value":NaN}', None, "invalid JSON body"),
        (b'{"value":1,"value":2}', None, "invalid JSON body"),
        (b"[]", None, "JSON body must be an object"),
    ],
)
def test_bounded_json_rejects_invalid_declared_and_structural_payloads(body, headers, detail):
    async def scenario() -> None:
        with pytest.raises(ClientPayloadError) as exc:
            await read_bounded_json(_request(body, headers), 100)
        assert exc.value.status == 400
        assert exc.value.detail == detail

    asyncio.run(scenario())


def test_bounded_json_defaults_an_empty_body_to_an_object():
    assert asyncio.run(read_bounded_json(_request(b""), 100)) == {}


def test_public_file_projections_delegate_to_the_closed_team_contract():
    file_id = "a" * 32
    metadata = {
        "id": file_id,
        "name": "report.txt",
        "media_type": "text/plain",
        "size": 7,
        "sha256": "b" * 64,
        "created_at": 1,
    }
    usage = {"used_bytes": 7, "limit_bytes": 8, "remaining_bytes": 1}
    assert projections.public_file_metadata(metadata) == metadata
    assert projections.public_file_upload({"team_id": "team", "file": {**metadata, **usage}}, "team") == {
        "file": metadata,
        **usage,
    }
    assert projections.public_file_inventory({"team_id": "team", "files": [metadata], **usage}, "team") == {
        "files": [metadata],
        **usage,
    }
    assert projections.public_file_deletion(
        {"team_id": "team", "id": file_id, "deleted": True, **usage}, "team", file_id
    ) == {"id": file_id, "deleted": True, **usage}


@pytest.mark.parametrize(
    "value",
    [
        None,
        {"assistants": [None]},
        {"assistants": [{"assistant": "Invalid", "status": "running"}]},
        {
            "assistants": [
                {"assistant": "assistant", "status": "running"},
                {"assistant": "assistant", "status": "stopped"},
            ]
        },
        {"assistants": [{"assistant": "assistant", "status": None}]},
    ],
)
def test_assistant_inventory_rejects_ambiguous_controller_data(value):
    assert projections.assistant_inventory(value) is None


@pytest.mark.parametrize(
    "value",
    [
        None,
        {"assistants": [None]},
        {"assistants": [{"assistant": "Invalid", "status": "running"}]},
        {
            "assistants": [
                {"assistant": "assistant", "status": "running"},
                {"assistant": "assistant", "status": "running"},
            ]
        },
        {"assistants": [{"assistant": "assistant", "status": None}]},
        {
            "assistants": [
                {"assistant": f"assistant-{index}", "status": "running"} for index in range(MAX_CHAT_ASSISTANTS + 1)
            ]
        },
    ],
)
def test_running_inventory_rejects_ambiguous_controller_data(value):
    assert projections.running_assistant_inventory(value) is None
