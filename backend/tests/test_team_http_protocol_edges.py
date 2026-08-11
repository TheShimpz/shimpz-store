"""Edge coverage for the vendored Team HTTP protocol primitives."""

from __future__ import annotations

import pytest

from app.protocol.http.v1 import payload, progress, websocket


class _Unencodable(str):
    def encode(self, *_args, **_kwargs):
        raise UnicodeError


def _file(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "id": "a" * 32,
        "name": "report.txt",
        "media_type": "text/plain",
        "size": 7,
        "sha256": "b" * 64,
        "created_at": 1,
    }
    value.update(changes)
    return value


@pytest.mark.parametrize(
    ("validator", "value"),
    [
        (payload.canonical_team_id, None),
        (payload.canonical_assistant_id, None),
        (payload.canonical_assistant_id, "a" * 81),
        (payload.canonical_assistant_id, "Bad"),
        (payload.canonical_source_digest, None),
        (payload.canonical_assurance_handle, None),
        (payload.canonical_file_id, None),
    ],
)
def test_identifier_validators_reject_noncanonical_values(validator, value):
    assert validator(value) is None


@pytest.mark.parametrize("value", [None, "", " " + "a", "a" * 81, "bad\nname"])
def test_team_name_rejects_every_invalid_shape(value):
    assert payload.canonical_team_name(value) is None


@pytest.mark.parametrize(
    "value",
    [None, "", " padded", "a" * 256, ".", "..", "a/b", "a\\b", "a\x7f"],
)
def test_filename_rejects_every_invalid_shape(value):
    assert payload.canonical_filename(value) is None


def test_filename_rejects_unencodable_unicode():
    assert payload.canonical_filename(_Unencodable("x")) is None


@pytest.mark.parametrize("value", [None, "", "TEXT/PLAIN"])
def test_media_type_defaults_and_normalizes(value):
    expected = "application/octet-stream" if value in {None, ""} else "text/plain"
    assert payload.canonical_media_type(value) == expected


@pytest.mark.parametrize("value", [7, "x" * 128, "not a/type"])
def test_media_type_rejects_invalid_values(value):
    assert payload.canonical_media_type(value) is None


@pytest.mark.parametrize("value", [True, "1", -1])
def test_integer_rejects_noncanonical_values(value):
    assert payload._integer(value) is None


@pytest.mark.parametrize(
    "value",
    [
        None,
        {"used_bytes": True, "limit_bytes": 1, "remaining_bytes": 0},
        {"used_bytes": 0, "limit_bytes": 0, "remaining_bytes": 0},
        {"used_bytes": 0, "limit_bytes": 1, "remaining_bytes": "1"},
        {"used_bytes": 1, "limit_bytes": 3, "remaining_bytes": 1},
    ],
)
def test_storage_usage_rejects_invalid_arithmetic(value):
    assert payload.project_storage_usage(value) is None


def test_storage_usage_accepts_within_and_over_quota_values():
    assert payload.project_storage_usage({"used_bytes": 1, "limit_bytes": 3, "remaining_bytes": 2})
    assert payload.project_storage_usage({"used_bytes": 4, "limit_bytes": 3, "remaining_bytes": 0})


@pytest.mark.parametrize(
    "value",
    [
        None,
        _file(id="bad"),
        _file(name="bad/name"),
        _file(media_type="bad"),
        _file(size=0),
        _file(size=payload.MAX_FILE_UPLOAD_BYTES + 1),
        _file(sha256=7),
        _file(sha256="bad"),
        _file(created_at=0),
    ],
)
def test_file_metadata_rejects_each_invalid_field(value):
    assert payload.project_file_metadata(value, include_usage=False) is None


def test_file_metadata_requires_valid_usage_when_requested():
    value = _file(used_bytes=7, limit_bytes=8, remaining_bytes=1)
    assert payload.project_file_metadata(value, include_usage=True) == value
    assert payload.project_file_metadata(_file(), include_usage=True) is None


def test_storage_response_projects_all_kinds_and_team_visibility():
    team_id = "marketing"
    file_value = _file(used_bytes=7, limit_bytes=8, remaining_bytes=1)
    upload = {"team_id": team_id, "file": file_value}
    projected_upload = payload.project_storage_response(
        upload, kind="upload", expected_team_id=team_id, include_team_id=False
    )
    assert projected_upload == {
        "file": _file(),
        "used_bytes": 7,
        "limit_bytes": 8,
        "remaining_bytes": 1,
    }
    listing = {
        "team_id": team_id,
        "files": [_file()],
        "used_bytes": 7,
        "limit_bytes": 8,
        "remaining_bytes": 1,
    }
    assert (
        payload.project_storage_response(listing, kind="list", expected_team_id=team_id, include_team_id=True)
        == listing
    )
    deletion = {
        "team_id": team_id,
        "id": "a" * 32,
        "deleted": True,
        "used_bytes": 0,
        "limit_bytes": 8,
        "remaining_bytes": 8,
    }
    assert (
        payload.project_storage_response(
            deletion,
            kind="delete",
            expected_team_id=team_id,
            expected_file_id="a" * 32,
            include_team_id=True,
        )
        == deletion
    )


@pytest.mark.parametrize(
    ("value", "kind", "expected_file_id"),
    [
        (None, "list", None),
        ({"team_id": "other"}, "list", None),
        ({"team_id": "team", "file": None}, "upload", None),
        ({"team_id": "team", "files": None}, "list", None),
        ({"team_id": "team", "files": [{}]}, "list", None),
        ({"team_id": "team", "files": [_file(), _file()]}, "list", None),
        ({"team_id": "team", "id": "bad", "deleted": True}, "delete", None),
        ({"team_id": "team", "id": "a" * 32, "deleted": True}, "delete", "b" * 32),
        ({"team_id": "team", "id": "a" * 32, "deleted": "yes"}, "delete", None),
        ({"team_id": "team", "id": "a" * 32, "deleted": True}, "delete", None),
        ({"team_id": "team"}, "unknown", None),
    ],
)
def test_storage_response_fails_closed(value, kind, expected_file_id):
    assert (
        payload.project_storage_response(
            value,
            kind=kind,
            expected_team_id="team",
            expected_file_id=expected_file_id,
            include_team_id=False,
        )
        is None
    )


def test_storage_response_rejects_oversized_file_list():
    value = {
        "team_id": "team",
        "files": [{}] * (payload.MAX_TEAM_FILES + 1),
    }
    assert payload.project_storage_response(value, kind="list", expected_team_id="team", include_team_id=False) is None


@pytest.mark.parametrize(
    "value",
    [
        None,
        {"phase": "model", "state": "invalid", "seq": 1},
        {"phase": "model", "state": "started", "seq": 1, "extra": True},
        {"phase": "model", "state": "started", "seq": True},
        {"phase": "model", "state": "finished", "seq": 1, "elapsed_ms": -1},
        {
            "phase": "action",
            "state": "started",
            "seq": 1,
            "assistant_id": "Bad",
            "index": 1,
            "action": "list-zones",
            "total": 1,
        },
        {
            "phase": "action",
            "state": "started",
            "seq": 1,
            "assistant_id": "assistant",
            "index": 2,
            "action": "list-zones",
            "total": 1,
        },
        {
            "phase": "action",
            "state": "started",
            "seq": 1,
            "assistant_id": "assistant",
            "index": 1,
            "action": "Bad",
            "total": 1,
        },
    ],
)
def test_progress_event_rejects_invalid_shapes(value):
    with pytest.raises(progress.ProgressContractError):
        progress.canonical_event(value)


def test_progress_event_projects_finished_action():
    event = {
        "seq": 1,
        "phase": "action",
        "state": "finished",
        "elapsed_ms": 0,
        "assistant_id": "assistant",
        "index": 1,
        "action": "list-zones",
        "total": 1,
    }
    assert progress.canonical_event(event) == event


@pytest.mark.parametrize(
    "value",
    [
        None,
        {"type": "terminal", "status": 200},
        {"type": "terminal", "status": True, "body": {}},
        {"type": "unknown"},
    ],
)
def test_progress_record_rejects_invalid_shapes(value):
    with pytest.raises(progress.ProgressContractError):
        progress.canonical_record(value)


def test_progress_record_projects_terminal():
    value = {"type": "terminal", "status": 200, "body": {"ok": True}}
    assert progress.canonical_record(value) == value


def test_progress_encoding_translates_json_and_size_failures(monkeypatch):
    with pytest.raises(progress.ProgressContractError, match="not JSON"):
        progress.encode_record({"type": "terminal", "status": 200, "body": {"bad": object()}})
    monkeypatch.setattr(progress, "MAX_LINE_BYTES", 1)
    with pytest.raises(progress.ProgressContractError, match="exceeds"):
        progress.encode_record({"type": "terminal", "status": 200, "body": {}})


@pytest.mark.parametrize("raw", [None, b"{}", b"", b" " * progress.MAX_LINE_BYTES + b"\n"])
def test_progress_line_rejects_invalid_framing(raw):
    with pytest.raises(progress.ProgressContractError, match="line"):
        progress.decode_line(raw)


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}\n', b'{"x":NaN}\n', b"\xff\n"])
def test_progress_line_rejects_invalid_json(raw):
    with pytest.raises(progress.ProgressContractError, match="JSON"):
        progress.decode_line(raw)


def test_progress_line_enforces_progress_specific_limit(monkeypatch):
    raw = progress.encode_record({"type": "progress", "seq": 1, "phase": "model", "state": "started"})
    monkeypatch.setattr(progress, "MAX_PROGRESS_LINE_BYTES", len(raw) - 1)
    with pytest.raises(progress.ProgressContractError, match="progress line"):
        progress.decode_line(raw)


@pytest.mark.parametrize(
    "value", [None, "null", "http://[bad", "ftp://example.com", "http://u@example.com", "http://example.com/path"]
)
def test_origin_rejects_invalid_values(value):
    assert websocket.canonical_origin(value) is None


def test_origin_normalizes_scheme_and_host():
    assert websocket.canonical_origin("HTTPS://EXAMPLE.COM:443") == "https://example.com:443"


def test_websocket_text_and_frame_helpers_cover_failures():
    assert websocket.public_text("safe", 10, field="title") == "safe"
    with pytest.raises(ValueError):
        websocket.public_text(" bad", 10, field="title")
    with pytest.raises(ValueError):
        websocket.unique_json_object([("x", 1), ("x", 2)])
    with pytest.raises(ValueError):
        websocket._reject_json_constant("NaN")
    failures = [
        ({"type": "bad"}, 10, 400),
        ({"type": "websocket.receive", "bytes": b"{}"}, 10, 415),
        ({"type": "websocket.receive", "text": _Unencodable("{}")}, 10, 400),
        ({"type": "websocket.receive", "text": "{}"}, 1, 413),
        ({"type": "websocket.receive", "text": "{"}, 10, 400),
        ({"type": "websocket.receive", "text": "[]"}, 10, 400),
    ]
    for message, maximum, status in failures:
        with pytest.raises(websocket.FrameError) as exc:
            websocket.decode_bounded_json_frame(message, maximum)
        assert exc.value.status == status
    assert websocket.decode_bounded_json_frame({"type": "websocket.receive", "text": "{}"}, 2) == {}


@pytest.mark.parametrize(("value", "expected"), [(400, 400), (True, 502), (399, 502), (600, 502)])
def test_safe_status_is_closed(value, expected):
    assert websocket.safe_status(value) == expected


def test_error_terminal_redacts_unsafe_detail():
    assert websocket.error_terminal(404, "safe", fallback_detail="fallback", max_detail_chars=10)["detail"] == "safe"
    for detail in ("", "too long here", "bad\n"):
        assert (
            websocket.error_terminal(None, detail, fallback_detail="fallback", max_detail_chars=10)["detail"]
            == "fallback"
        )


def test_challenge_identity_is_fail_closed():
    challenge = "a" * 32
    assert websocket.challenge_identity(None, "team") is None
    assert websocket.challenge_identity({"team_id": "other"}, "team") is None
    assert websocket.challenge_identity({"team_id": "team", "challenge_id": "bad", "turn_id": "bad"}, "team") is None
    assert (
        websocket.challenge_identity({"team_id": "team", "challenge_id": challenge, "turn_id": "b" * 32}, "team")
        is None
    )
    assert websocket.challenge_identity(
        {"team_id": "team", "challenge_id": challenge, "turn_id": challenge}, "team"
    ) == (challenge, challenge)


@pytest.mark.parametrize(
    "value",
    [
        None,
        {"type": "bad", "decision": "deny", "challenge_id": "a" * 32},
        {"type": "human-response", "decision": "bad", "challenge_id": "a" * 32},
        {"type": "human-response", "decision": "deny", "challenge_id": "bad"},
        {"type": "human-response", "decision": "deny", "challenge_id": "a" * 32, "value": True},
        {"type": "human-response", "decision": "submit", "challenge_id": "a" * 32, "value": False},
    ],
)
def test_human_response_rejects_invalid_frames(value):
    with pytest.raises(websocket.FrameError):
        websocket.canonical_human_response(value)


@pytest.mark.parametrize("value", [True, "", "x", ["a"], ["a", "a"], [1], ["x" * 129], ["x"] * 33])
def test_human_value_is_closed(value):
    expected = value is True or value == "" or value == "x" or value == ["a"]
    assert websocket._human_value(value) is expected


def test_human_response_accepts_submit_and_deny():
    challenge = "a" * 32
    submit = {"type": "human-response", "challenge_id": challenge, "decision": "submit", "value": True}
    deny = {"type": "human-response", "challenge_id": challenge, "decision": "deny"}
    assert websocket.canonical_human_response(submit) == submit
    assert websocket.canonical_human_response(deny) == deny
