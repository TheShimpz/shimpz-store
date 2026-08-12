"""Edge coverage for public chat events and the bounded NDJSON relay."""

from __future__ import annotations

import asyncio

import pytest

from app.chat import events, relay
from app.payloads import ClientPayloadError


def _base_request(kind="approval"):
    return {
        "kind": kind,
        "ordinal": 0,
        "title": "Title",
        "description": "Description",
        "fingerprint": "a" * 64,
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"message": 1, "files": [], "assistant_ids": []},
        {"message": " ", "files": [], "assistant_ids": []},
        {"message": "x" * (events.MAX_CHAT_MESSAGE_CHARS + 1), "files": [], "assistant_ids": []},
        {"message": "ok", "files": None, "assistant_ids": []},
        {"message": "ok", "files": ["bad"], "assistant_ids": []},
    ],
)
def test_chat_turn_rejects_invalid_message_and_files(payload):
    with pytest.raises(ClientPayloadError):
        events.chat_turn_payload(payload)


def test_error_and_text_projection_reject_invalid_shapes():
    assert events._validated_error_event({"type": "error"}) is None
    assert events._public_text(None, 10) is None
    assert events._human_identity(None, "name", 80) is None
    assert events._human_identity({"id": "Invalid", "name": "Name"}, "name", 80) is None
    assert events._human_assistant(None) is None
    assert events._human_assistant({"id": "Invalid", "name": "Name", "version": "0.4.2"}) is None


def test_human_request_helpers_reject_invalid_base_and_input():
    assert events._human_request_base(None) is None
    invalid_base = _base_request()
    invalid_base["ordinal"] = True
    assert events._human_request_base(invalid_base) is None
    assert events._human_input_base({"label": None, "required": True}, _base_request()) is None

    text = {**_base_request("input:text"), "label": "Label", "required": True}
    assert events._human_text_request(text, _base_request("input:text"), 10) is None


def test_human_options_reject_shape_fields_values_and_duplicates():
    assert events._human_options([]) is None
    assert events._human_options([None, None]) is None
    assert (
        events._human_options(
            [
                {"value": "a", "label": "A", "description": None},
                {"value": "b", "label": "B", "description": "bad\nvalue"},
            ]
        )
        is None
    )
    assert (
        events._human_options(
            [
                {"value": "a", "label": "A", "description": None},
                {"value": "a", "label": "Again", "description": None},
            ]
        )
        is None
    )


def test_human_choice_rejects_invalid_shape_and_selection_bounds():
    base = _base_request("input:choice")
    assert events._human_choice_request(base, base, multiple=False) is None
    choices = {
        **_base_request("input:choices"),
        "label": "Choose",
        "required": True,
        "options": [
            {"value": "a", "label": "A", "description": None},
            {"value": "b", "label": "B", "description": None},
        ],
        "min_selections": 2,
        "max_selections": 1,
    }
    assert events._human_choice_request(choices, _base_request("input:choices"), multiple=True) is None
    assert events._human_request(None) is None


def test_terminal_and_stream_projection_reject_nonobjects_and_blank_lines():
    assert events.validated_terminal_event(None, "team") is None
    assert events.parsed_stream_event(b"  ", "team") is None


class _Chunks:
    def __init__(self, *chunks):
        self.chunks = iter((*chunks, b""))

    def read1(self, _maximum):
        return next(self.chunks)


def test_relay_enforces_total_line_and_trailing_limits(monkeypatch):
    monkeypatch.setattr(relay, "MAX_UPSTREAM_STREAM_BYTES", 2)
    with pytest.raises(relay._StreamLimitError, match="total"):
        list(relay._bounded_upstream_lines(_Chunks(b"abc")))

    monkeypatch.setattr(relay, "MAX_UPSTREAM_STREAM_BYTES", 100)
    monkeypatch.setattr(relay, "MAX_UPSTREAM_STREAM_LINE_BYTES", 2)
    with pytest.raises(relay._StreamLimitError, match="line"):
        list(relay._bounded_upstream_lines(_Chunks(b"abc")))
    with pytest.raises(relay._StreamLimitError, match="line"):
        list(relay._bounded_upstream_lines(_Chunks(b"abc\n")))
    with pytest.raises(relay._StreamLimitError, match="line"):
        list(relay._bounded_upstream_lines(_Chunks(b"\nabc")))


def test_relay_ignores_blank_lines_before_one_terminal(monkeypatch):
    monkeypatch.setattr(relay, "_parsed_stream_event", lambda line, _team: {"type": "done", "line": line.decode()})
    assert relay._relay_upstream_events(_Chunks(b"\nvalue\n"), "team") == {
        "type": "done",
        "line": "value",
    }


def test_stream_transport_translates_socket_failure_and_signals_start(monkeypatch):
    class Connection:
        def __init__(self, *_args, **_kwargs):
            pass

        def request(self, *_args, **_kwargs):
            raise OSError("failed")

        def close(self):
            pass

    monkeypatch.setattr(relay.http.client, "HTTPConnection", Connection)

    async def scenario():
        loop = asyncio.get_running_loop()
        started = asyncio.Event()
        turn = relay._StreamRelay("team", "hello", {}, loop, started)
        result = relay._stream_lines(turn)
        await asyncio.sleep(0)
        assert started.is_set()
        assert result["status"] == 502
        assert result["_relay_abort"] is True

    asyncio.run(scenario())
