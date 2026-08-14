"""Edge coverage for the Local Supervisor assertion mirror."""

from __future__ import annotations

import pytest

from app.protocol.http.v1 import supervisor


class _Unencodable(str):
    def encode(self, *_args, **_kwargs):
        raise UnicodeError


def _claims() -> dict[str, object]:
    return {
        "v": 1,
        "aud": "team-local",
        "sub": "a" * 32,
        "session_sha256": "b" * 64,
        "jti": "c" * 32,
        "iat": 2_200_000_000,
        "exp": 2_200_000_015,
        "method": "POST",
        "path": "/v1/teams/team/chat",
        "body": {"kind": "json", "length": 2, "sha256": "d" * 64},
    }


def test_integer_and_digest_reject_invalid_values():
    with pytest.raises(supervisor.SupervisorAssertionError):
        supervisor._integer(True, label="time")
    with pytest.raises(supervisor.SupervisorAssertionError):
        supervisor._digest("bad", label="digest")


def test_empty_body_requires_exact_zero_length_digest():
    with pytest.raises(supervisor.SupervisorAssertionError):
        supervisor._body(None)
    with pytest.raises(supervisor.SupervisorAssertionError):
        supervisor._body({"kind": "none", "length": 1, "sha256": supervisor.EMPTY_SHA256})
    with pytest.raises(supervisor.SupervisorAssertionError):
        supervisor._body({"kind": "none", "length": 0, "sha256": "a" * 64})
    value = {"kind": "none", "length": 0, "sha256": supervisor.EMPTY_SHA256}
    assert supervisor._body(value) == value


def test_json_body_rejects_invalid_length():
    with pytest.raises(supervisor.SupervisorAssertionError):
        supervisor._body({"kind": "json", "length": 1, "sha256": "a" * 64})


@pytest.mark.parametrize(
    "changes",
    [
        {"length": 0},
        {"filename": ""},
        {"filename": _Unencodable("name")},
        {"filename": "bad/name"},
        {"media_type": "bad"},
    ],
)
def test_file_body_rejects_invalid_metadata(changes):
    value = {"kind": "file", "length": 1, "filename": "name.txt", "media_type": "text/plain"}
    value.update(changes)
    with pytest.raises(supervisor.SupervisorAssertionError):
        supervisor._body(value)


def test_file_body_projects_valid_metadata_and_unknown_kind_fails():
    value = {"kind": "file", "length": 1, "filename": "name.txt", "media_type": "text/plain"}
    assert supervisor._body(value) == value
    with pytest.raises(supervisor.SupervisorAssertionError):
        supervisor._body({"kind": "unknown"})


def test_model_binding_requires_exact_identity_and_digest():
    with pytest.raises(supervisor.SupervisorAssertionError):
        supervisor._model(None)
    with pytest.raises(supervisor.SupervisorAssertionError):
        supervisor._model({"provider": "Bad", "key_sha256": "a" * 64})
    value = {"provider": "openai", "key_sha256": "a" * 64}
    assert supervisor._model(value) == value


def test_assurance_binding_requires_exact_identity():
    with pytest.raises(supervisor.SupervisorAssertionError):
        supervisor._assurance(None)
    with pytest.raises(supervisor.SupervisorAssertionError):
        supervisor._assurance({"kind": "unknown", "challenge_id": "a" * 32})


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.clear(),
        lambda value: value.update(extra=True),
        lambda value: value.update(v=2),
        lambda value: value.update(sub="bad"),
        lambda value: value.update(jti="bad"),
        lambda value: value.update(method="PATCH"),
    ],
)
def test_claims_reject_each_closed_envelope_violation(mutate):
    value = _claims()
    mutate(value)
    with pytest.raises(supervisor.SupervisorAssertionError):
        supervisor.canonical_claims(value)


def test_claims_reject_non_object_and_project_optional_bindings():
    with pytest.raises(supervisor.SupervisorAssertionError):
        supervisor.canonical_claims(None)
    value = _claims()
    value["model"] = {"provider": "openai", "key_sha256": "e" * 64}
    value["assurance"] = {"kind": "auth:password", "challenge_id": "f" * 32}
    assert supervisor.canonical_claims(value) == value
    without_optional = _claims()
    assert supervisor.canonical_claims(without_optional) == without_optional


def test_canonical_json_is_deterministic_bounded_and_strict(monkeypatch):
    assert supervisor.canonical_json({"b": 2, "a": 1}) == b'{"a":1,"b":2}'
    with pytest.raises(supervisor.SupervisorAssertionError, match="invalid"):
        supervisor.canonical_json({"bad": object()})
    monkeypatch.setattr(supervisor, "ASSERTION_MAX_BYTES", 1)
    with pytest.raises(supervisor.SupervisorAssertionError, match="exceeds"):
        supervisor.canonical_json({})


def test_claims_json_validates_before_encoding():
    value = _claims()
    assert supervisor.claims_json(value) == supervisor.canonical_json(value)
