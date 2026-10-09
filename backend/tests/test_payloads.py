"""Bounded duplicate-safe JSON request parsing."""

import asyncio

import pytest
from fastapi import Request

from app.payloads import ClientPayloadError, read_bounded_json


def _request(chunks: list[bytes], length: str | None = None) -> Request:
    """Return a request that delivers each chunk in turn and then reports a client disconnect."""
    pending = list(chunks)
    headers = [] if length is None else [(b"content-length", length.encode())]

    async def receive() -> dict[str, object]:
        if not pending:
            return {"type": "http.disconnect"}
        return {"type": "http.request", "body": pending.pop(0), "more_body": bool(pending)}

    return Request({"type": "http", "headers": headers}, receive)


@pytest.mark.parametrize(
    ("chunks", "length", "status"),
    [
        ([b"{}"], "two", 400),
        ([b"{}"], "-1", 400),
        ([b"{}"], "33", 413),
        ([b'{"a":"' + b"x" * 16, b"x" * 16 + b'"}'], None, 413),
        ([b'{"a":1,"a":2}'], None, 400),
        ([b"[]"], None, 400),
    ],
)
def test_read_refuses_invalid_length_oversize_duplicate_keys_and_non_objects(chunks, length, status) -> None:
    with pytest.raises(ClientPayloadError) as exc:
        asyncio.run(read_bounded_json(_request(chunks, length), 32))
    assert exc.value.status == status


def test_read_admits_one_bounded_object_and_an_empty_body() -> None:
    assert asyncio.run(read_bounded_json(_request([b'{"a":', b"1}"], "7"), 32)) == {"a": 1}
    assert asyncio.run(read_bounded_json(_request([b""]), 32)) == {}
