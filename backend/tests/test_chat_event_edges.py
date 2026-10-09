"""Edge coverage for public chat events and the bounded NDJSON relay."""

import asyncio
import hashlib

import pytest

from app.chat import events, relay
from app.payloads import ClientPayloadError


def _reference(text, **params):
    return {"message": hashlib.sha256(text.encode()).hexdigest(), "params": params}


def _base_request(kind="approval"):
    return {
        "kind": kind,
        "ordinal": 0,
        "title": _reference("Title"),
        "description": _reference("Description"),
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
    assert events._human_request_base(_base_request()) == _base_request()
    invalid_base = _base_request()
    invalid_base["ordinal"] = True
    assert events._human_request_base(invalid_base) is None
    assert events._human_request_base({**_base_request(), "title": "Title"}) is None
    assert events._human_input_base({"label": None, "required": True}, _base_request()) is None
    assert events._human_input_base({"label": "Label", "required": True}, _base_request()) is None

    text = {**_base_request("input:text"), "label": _reference("Label"), "required": True}
    assert events._human_text_request(text, _base_request("input:text"), 10) is None
    complete = {**text, "placeholder": None, "min_length": 1, "max_length": 10}
    assert events._human_text_request(complete, _base_request("input:text"), 10)["placeholder"] is None
    referenced = {**complete, "placeholder": _reference("Example: {zone}", zone="example.com")}
    assert events._human_text_request(referenced, _base_request("input:text"), 10)["placeholder"] == _reference(
        "Example: {zone}", zone="example.com"
    )
    assert events._human_text_request({**complete, "placeholder": "Example"}, _base_request("input:text"), 10) is None


@pytest.mark.parametrize(
    "reference",
    [
        _reference("Delete {count} records in {zone}.", count=0, zone="example.com"),
        _reference("Rotate {key}.", key="Key_1.a:b-c"),
        _reference("Publish {count}.", count=10**15 - 1),
        _reference("Authorize {name}.", name="_acme-challenge.example.com"),
        _reference("Authorize {name}.", name="_dmarc"),
        _reference("Authorize {name}.", name=("a" * 63 + ".") * 3 + "b" * 61),
        _reference("Eight", **{f"p{index}": index for index in range(8)}),
    ],
)
def test_copy_references_admit_their_closed_shape_and_parameter_grammar(reference):
    assert events._copy_reference(reference) == reference


@pytest.mark.parametrize(
    "reference",
    [
        "Title",
        None,
        {"message": "a" * 64},
        {**_reference("x"), "text": "x"},
        {"message": "A" * 64, "params": {}},
        {"message": "a" * 63, "params": {}},
        {"message": 1, "params": {}},
        {"message": "a" * 64, "params": []},
        _reference("Nine", **{f"p{index}": index for index in range(9)}),
        _reference("Name", Zone="example.com"),
        _reference("Count", count=True),
        _reference("Count", count=-1),
        _reference("Count", count=10**15),
        _reference("Count", count=1.0),
        _reference("Prose", value="two words"),
        _reference("Long", value="a" * 129),
        _reference("Domain", zone=("a" * 63 + ".") * 4 + "com"),
        _reference("Wildcard", name="*.example.com"),
        _reference("Trailing dot", name="_dmarc.example.com."),
        _reference("Empty label", name="_dmarc..example.com"),
        _reference("Uppercase", name="_DMARC.example.com"),
        _reference("Overlong", name=("a" * 63 + ".") * 3 + "b" * 62),
        _reference("Nested", value={"a": 1}),
    ],
)
def test_copy_references_refuse_every_other_shape(reference):
    assert events._copy_reference(reference) is None


def test_human_options_reject_shape_fields_values_and_duplicates():
    assert events._human_options([]) is None
    assert events._human_options([None, None]) is None
    admitted = [
        {"value": "a", "label": _reference("A"), "description": None},
        {"value": "b", "label": _reference("B"), "description": _reference("Second")},
    ]
    assert events._human_options(admitted) == admitted
    for invalid in (
        [admitted[0], {**admitted[1], "description": "Second"}],
        [admitted[0], {**admitted[1], "label": "B"}],
        [admitted[0], {**admitted[1], "value": "bad\nvalue"}],
        [admitted[0], {**admitted[1], "value": "a"}],
    ):
        assert events._human_options(invalid) is None


def test_human_choice_rejects_invalid_shape_and_selection_bounds():
    base = _base_request("input:choice")
    assert events._human_choice_request(base, base, multiple=False) is None
    choices = {
        **_base_request("input:choices"),
        "label": _reference("Choose"),
        "required": True,
        "options": [
            {"value": "a", "label": _reference("A"), "description": None},
            {"value": "b", "label": _reference("B"), "description": None},
        ],
        "min_selections": 2,
        "max_selections": 1,
    }
    assert events._human_choice_request(choices, _base_request("input:choices"), multiple=True) is None
    assert events._human_request(None) is None


def test_terminal_and_stream_projection_reject_nonobjects_and_blank_lines():
    assert events.validated_terminal_event(None, "team") is None
    assert events.parsed_stream_event(b"  ", "team") is None


_DONE = {"type": "done", "team_id": "team_1", "team_name": "Marketing", "reply": "Ready.", "clarification": None}
_USAGE = {
    "duration_ms": 6200,
    "models": [{"provider": "openai", "model": "gpt-6-luna", "input_tokens": 1331, "output_tokens": 36}],
}


def test_done_relays_only_a_closed_turn_usage():
    assert events.validated_terminal_event(dict(_DONE), "team_1") == _DONE
    assert events.validated_terminal_event({**_DONE, "usage": _USAGE}, "team_1") == {**_DONE, "usage": _USAGE}
    for invalid in (None, {**_USAGE, "models": []}, {**_USAGE, "cost": 1}):
        assert events.validated_terminal_event({**_DONE, "usage": invalid}, "team_1") is None
    assert events.validated_terminal_event({**_DONE, "usage": _USAGE, "trace_id": "a" * 32}, "team_1") is None


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
