"""Failure coverage for the generated Team HTTP integrity verifier."""

from __future__ import annotations

import hashlib
import importlib
import json
import runpy
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

PROTOCOL = Path(__file__).resolve().parents[1] / "app" / "protocol" / "http" / "v1"
DEPENDENCIES = ("payload", "progress", "routine", "supervisor", "websocket")


def _refresh_manifest(root: Path) -> None:
    rows = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
        for path in sorted(root.iterdir())
        if path.is_file() and path.name != "contract-files.sha256"
    ]
    (root / "contract-files.sha256").write_text("\n".join(rows) + "\n", encoding="ascii")


def _vectors(root: Path, mutate: Callable[[dict], None]) -> None:
    path = root / "vectors.json"
    value = json.loads(path.read_bytes())
    mutate(value)
    path.write_text(json.dumps(value, separators=(",", ":")), encoding="utf-8")
    _refresh_manifest(root)


def _execute(
    root: Path,
    *,
    patch: Callable[[dict[str, ModuleType]], None] | None = None,
) -> None:
    saved = {name: sys.modules.pop(name, None) for name in DEPENDENCIES}
    original_resolve = Path.resolve

    def scoped_resolve(path: Path, *args, **kwargs) -> Path:
        if path == PROTOCOL / "verify.py":
            return root / "verify.py"
        return original_resolve(path, *args, **kwargs)

    sys.path.insert(0, str(root))
    Path.resolve = scoped_resolve
    try:
        modules = {name: importlib.import_module(name) for name in DEPENDENCIES}
        if patch is not None:
            patch(modules)
        runpy.run_path(str(PROTOCOL / "verify.py"), run_name="__main__")
    finally:
        Path.resolve = original_resolve
        sys.path.remove(str(root))
        for name in DEPENDENCIES:
            sys.modules.pop(name, None)
            if saved[name] is not None:
                sys.modules[name] = saved[name]


def _copy(tmp_path: Path) -> Path:
    root = tmp_path / "v1"
    shutil.copytree(PROTOCOL, root)
    return root


def test_verifier_rejects_malformed_and_duplicate_manifest_rows(tmp_path):
    malformed = _copy(tmp_path / "malformed")
    (malformed / "contract-files.sha256").write_text("invalid\n", encoding="ascii")
    with pytest.raises(SystemExit, match="manifest is invalid"):
        _execute(malformed)

    duplicate = _copy(tmp_path / "duplicate")
    manifest = duplicate / "contract-files.sha256"
    first = manifest.read_text(encoding="ascii").splitlines()[0]
    manifest.write_text(f"{first}\n{first}\n", encoding="ascii")
    with pytest.raises(SystemExit, match="manifest is invalid"):
        _execute(duplicate)


def test_verifier_rejects_artifact_set_and_digest_drift(tmp_path):
    extra = _copy(tmp_path / "extra")
    (extra / "unexpected.txt").write_text("unexpected", encoding="utf-8")
    with pytest.raises(SystemExit, match="artifact set differs"):
        _execute(extra)

    changed = _copy(tmp_path / "changed")
    (changed / "README.md").write_text("changed", encoding="utf-8")
    with pytest.raises(SystemExit, match="SHA-256"):
        _execute(changed)


def test_verifier_rejects_invalid_vector_root_and_headers(tmp_path):
    root = _copy(tmp_path / "root")
    (root / "vectors.json").write_text("[]", encoding="utf-8")
    _refresh_manifest(root)
    with pytest.raises(SystemExit, match="invalid root"):
        _execute(root)

    headers = _copy(tmp_path / "headers")
    _vectors(headers, lambda value: value.update(headers={}))
    with pytest.raises(SystemExit, match="header vector differs"):
        _execute(headers)


def test_verifier_rejects_supervisor_vector_disagreement(tmp_path):
    positive = _copy(tmp_path / "positive")

    def wrong_positive(modules):
        modules["supervisor"].canonical_claims = lambda _case: {}

    with pytest.raises(SystemExit, match="positive vector differs"):
        _execute(positive, patch=wrong_positive)

    negative = _copy(tmp_path / "negative")

    def accepts_everything(modules):
        modules["supervisor"].canonical_claims = lambda case: case

    with pytest.raises(SystemExit, match="negative vector differs"):
        _execute(negative, patch=accepts_everything)


def test_verifier_rejects_frame_vector_disagreement(tmp_path):
    raised = _copy(tmp_path / "raised")

    def reject_valid(modules):
        error = modules["websocket"].FrameError

        def reject(*_args):
            raise error(400, "rejected")

        modules["websocket"].decode_bounded_json_frame = reject

    with pytest.raises(SystemExit, match="frame vector differs"):
        _execute(raised, patch=reject_valid)

    returned = _copy(tmp_path / "returned")

    def return_wrong(modules):
        modules["websocket"].decode_bounded_json_frame = lambda *_args: {}

    with pytest.raises(SystemExit, match="frame vector differs"):
        _execute(returned, patch=return_wrong)


def test_verifier_rejects_human_response_vector_disagreement(tmp_path):
    raised = _copy(tmp_path / "raised")

    def reject_valid(modules):
        error = modules["websocket"].FrameError

        def reject(*_args):
            raise error(400, "rejected")

        modules["websocket"].canonical_human_response = reject

    with pytest.raises(SystemExit, match="human response vector differs"):
        _execute(raised, patch=reject_valid)

    returned = _copy(tmp_path / "returned")

    def accept_everything(modules):
        modules["websocket"].canonical_human_response = lambda frame: frame

    with pytest.raises(SystemExit, match="human response vector differs"):
        _execute(returned, patch=accept_everything)


def test_verifier_rejects_stream_record_vector_disagreement(tmp_path):
    raised = _copy(tmp_path / "raised")

    def reject_valid(modules):
        error = modules["progress"].ProgressContractError

        def reject(*_args):
            raise error("rejected")

        modules["progress"].canonical_record = reject

    with pytest.raises(SystemExit, match="chat stream vector differs"):
        _execute(raised, patch=reject_valid)

    returned = _copy(tmp_path / "returned")

    def accept_everything(modules):
        modules["progress"].canonical_record = lambda record: record

    with pytest.raises(SystemExit, match="chat stream vector differs"):
        _execute(returned, patch=accept_everything)


def test_verifier_rejects_stream_line_vector_disagreement(tmp_path):
    raised = _copy(tmp_path / "raised")

    def reject_valid(modules):
        error = modules["progress"].ProgressContractError

        def reject(*_args):
            raise error("rejected")

        modules["progress"].decode_line = reject

    with pytest.raises(SystemExit, match="chat stream line vector differs"):
        _execute(raised, patch=reject_valid)

    returned = _copy(tmp_path / "returned")

    def return_wrong(modules):
        modules["progress"].decode_line = lambda _raw: {}

    with pytest.raises(SystemExit, match="chat stream line vector differs"):
        _execute(returned, patch=return_wrong)


def test_verifier_rejects_identifier_vector_disagreement(tmp_path):
    positive = _copy(tmp_path / "positive")

    def reject_valid(modules):
        modules["payload"].canonical_team_id = lambda _value: None

    with pytest.raises(SystemExit, match="team positive vector differs"):
        _execute(positive, patch=reject_valid)

    negative = _copy(tmp_path / "negative")

    def accept_everything(modules):
        modules["payload"].canonical_team_id = lambda value: value

    with pytest.raises(SystemExit, match="team negative vector differs"):
        _execute(negative, patch=accept_everything)


@pytest.mark.parametrize(
    ("function_name", "mode", "message"),
    [
        ("canonical_locale", "positive", "chat_locale positive"),
        ("canonical_locale", "negative", "chat_locale negative"),
        ("canonical_help_url", "positive", "help_url positive"),
        ("canonical_help_url", "negative", "help_url negative"),
        ("canonical_purpose", "positive", "purpose positive"),
        ("canonical_purpose", "negative", "purpose negative"),
        ("canonical_action_label", "positive", "Action-label label positive"),
        ("canonical_action_label", "negative", "Action-label label negative"),
    ],
)
def test_verifier_rejects_action_label_vector_drift(tmp_path, function_name, mode, message):
    root = _copy(tmp_path)

    def drift(modules):
        payload = modules["payload"]
        original = getattr(payload, function_name)

        def replace(value):
            canonical = original(value)
            if mode == "positive":
                return None if canonical is not None else canonical
            return "unexpected" if canonical is None else canonical

        setattr(payload, function_name, replace)

    with pytest.raises(SystemExit, match=message):
        _execute(root, patch=drift)


def test_verifier_rejects_missing_or_drifted_clarification_vectors(tmp_path):
    def missing(value):
        value["clarification"]["invalid"] = []

    def accepted_invalid(value):
        value["clarification"]["invalid"] = [value["clarification"]["valid"][0]]

    def rejected_valid(value):
        value["clarification"]["valid"] = [{**value["clarification"]["valid"][0], "extra": 1}]

    def drifted_rendering(value):
        value["clarification"]["rendered"][0] = "Something else"

    for name, mutate, message in (
        ("rendering", drifted_rendering, "a clarification rendering vector differs"),
        ("missing", missing, "clarification vectors are missing"),
        ("accepted", accepted_invalid, "an invalid clarification vector was admitted"),
        ("rejected", rejected_valid, "a valid clarification vector was not admitted exactly"),
    ):
        root = _copy(tmp_path / name)
        _vectors(root, mutate)
        with pytest.raises(SystemExit, match=message):
            _execute(root)


@pytest.mark.parametrize("family", ["chat_locale", "help_url", "purpose"])
def test_verifier_rejects_missing_presentation_vectors(tmp_path, family):
    root = _copy(tmp_path)

    def missing(value):
        value[family]["invalid"] = []

    _vectors(root, missing)
    with pytest.raises(SystemExit, match=f"Team HTTP {family} vectors are missing"):
        _execute(root)


def test_verifier_rejects_missing_or_drifted_rendered_copy_vectors(tmp_path):
    def missing(value):
        value["rendered_copy"]["invalid"] = []

    def accepted_invalid(value):
        value["rendered_copy"]["invalid"] = value["rendered_copy"]["valid"][:1]

    def rejected_valid(value):
        value["rendered_copy"]["valid"] = value["rendered_copy"]["invalid"][:1]

    for name, mutate, message in (
        ("missing", missing, "Team HTTP rendered copy vectors are missing"),
        ("accepted", accepted_invalid, "Team HTTP rendered copy negative vector differs"),
        ("rejected", rejected_valid, "Team HTTP rendered copy positive vector differs"),
    ):
        root = _copy(tmp_path / name)
        _vectors(root, mutate)
        with pytest.raises(SystemExit, match=message):
            _execute(root)


def test_verifier_rejects_missing_or_drifted_skill_vectors(tmp_path):
    def missing(value):
        value["skills"]["invalid"] = []

    def accepted_invalid(value):
        value["skills"]["invalid"] = [value["skills"]["valid"][1]]

    def rejected_valid(value):
        value["skills"]["valid"] = [[{"key": "procedure-000000000000", "contracts": {}, "steps": []}]]

    def drifted_apply(value):
        value["knowledge_apply"][0]["result"]["skills"] = []

    for name, mutate, message in (
        ("missing", missing, "skills vectors are missing"),
        ("accepted", accepted_invalid, "an invalid skills vector was admitted"),
        ("rejected", rejected_valid, "a valid skills vector was not admitted exactly"),
        ("apply", drifted_apply, "a knowledge application vector differs"),
    ):
        root = _copy(tmp_path / name)
        _vectors(root, mutate)
        with pytest.raises(SystemExit, match=message):
            _execute(root)


def test_verifier_rejects_missing_or_drifted_memory_vectors(tmp_path):
    def missing(value):
        value["memory"]["valid"] = []

    def accepted_invalid(value):
        value["memory_changes"]["invalid"] = [value["memory_changes"]["valid"][1]]

    def rejected_valid(value):
        value["memory"]["valid"] = [[{"topic": "Bad Topic", "preference": "x"}]]

    def drifted_apply(value):
        value["memory_apply"][0]["result"] = []

    for name, mutate, message in (
        ("missing", missing, "memory vectors are missing"),
        ("accepted", accepted_invalid, "an invalid memory_changes vector was admitted"),
        ("rejected", rejected_valid, "a valid memory vector was not admitted exactly"),
        ("apply", drifted_apply, "a memory application vector differs"),
    ):
        root = _copy(tmp_path / name)
        _vectors(root, mutate)
        with pytest.raises(SystemExit, match=message):
            _execute(root)


def test_verifier_rejects_missing_or_drifted_chat_conversation_vectors(tmp_path):
    def missing(value):
        value["chat_conversation"]["invalid"] = []

    def accepted_invalid(value):
        value["chat_conversation"]["invalid"] = [[]]

    def rejected_valid(value):
        value["chat_conversation"]["valid"] = [{"generated": "nine-entries"}]

    for name, mutate, message in (
        ("missing", missing, "conversation vectors are missing"),
        ("accepted", accepted_invalid, "conversation negative vector differs"),
        ("rejected", rejected_valid, "conversation positive vector differs"),
    ):
        root = _copy(tmp_path / name)
        _vectors(root, mutate)
        with pytest.raises(SystemExit, match=message):
            _execute(root)


def _set(path: tuple[str, ...], replacement):
    def mutate(value):
        target = value
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = replacement(value) if callable(replacement) else replacement

    return mutate


def test_verifier_rejects_missing_or_drifted_routine_vectors(tmp_path):
    views = ("routine_views",)
    cases = (
        (_set(("local_routine", "invalid"), []), "Local Routine vectors are missing"),
        (
            _set(("local_routine", "valid"), lambda v: [{**v["local_routine"]["valid"][0], "authority": "session"}]),
            "Local Routine positive vector differs",
        ),
        (
            _set(("local_routine", "invalid"), lambda v: [v["local_routine"]["valid"][0]]),
            "Local Routine negative vector",
        ),
        (_set(("routine_schedule", "daily_rate"), []), "routine schedule vectors are missing"),
        (_set(("routine_schedule", "valid"), [{"kind": "daily", "time": "25:00"}]), "valid routine schedule vector"),
        (
            _set(("routine_schedule", "invalid"), [{"kind": "daily", "time": "09:00"}]),
            "invalid routine schedule vector",
        ),
        (
            _set(
                ("routine_schedule", "daily_rate"), lambda v: [{**v["routine_schedule"]["daily_rate"][0], "rate": "5"}]
            ),
            "routine daily rate vector differs",
        ),
        (_set(("routine_timezone", "valid"), []), "routine timezone vectors are missing"),
        (_set(("routine_timezone", "valid"), ["../UTC"]), "valid routine timezone vector"),
        (_set(("routine_timezone", "invalid"), ["UTC"]), "invalid routine timezone vector"),
        (_set(("chat_request_identity", "valid"), []), "chat_request_identity vectors are missing"),
        (
            _set(("chat_request_identity", "invalid"), lambda v: [v["chat_request_identity"]["valid"][0]]),
            "chat_request_identity negative vector differs",
        ),
        (lambda v: v["routine_views"].pop("claim"), "routine view vectors are missing"),
        (_set((*views, "claim", "valid"), [{"run": None, "extra": 1}]), "valid routine claim vector"),
        (_set((*views, "claim", "invalid"), [{"run": None, "next_due_at": None}]), "invalid routine claim vector"),
        (lambda v: v.pop("routine_diagnostics"), "routine diagnostics vectors are missing"),
        (
            _set(("routine_diagnostics", "valid"), [{"team_id": "team_1", "run_id": "b" * 32}]),
            "valid routine diagnostics vector",
        ),
        (
            _set(("routine_diagnostics", "invalid"), [{"team_id": "team_1", "run_id": "b" * 32, "diagnostics": []}]),
            "invalid routine diagnostics vector",
        ),
    )
    for index, (mutate, message) in enumerate(cases):
        root = _copy(tmp_path / str(index))
        _vectors(root, mutate)
        with pytest.raises(SystemExit, match=message):
            _execute(root)
