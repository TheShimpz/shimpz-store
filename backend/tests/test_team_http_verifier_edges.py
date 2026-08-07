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
DEPENDENCIES = ("payload", "progress", "supervisor", "websocket")


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
