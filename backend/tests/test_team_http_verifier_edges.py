"""Failure coverage for the generated Team HTTP integrity verifier."""

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
DEPENDENCIES = (
    "identifiers",
    "payload",
    "phrase",
    "progress",
    "purpose",
    "routine",
    "routine_context",
    "routine_notice",
    "routine_proposal",
    "routine_run",
    "supervisor",
    "turn",
    "websocket",
)


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


@pytest.mark.parametrize(
    ("target", "error", "returned", "message"),
    [
        ("websocket.decode_bounded_json_frame", ("FrameError", 400), lambda *_args: {}, "frame vector differs"),
        (
            "websocket.canonical_human_response",
            ("FrameError", 400),
            lambda frame: frame,
            "human response vector differs",
        ),
        (
            "progress.canonical_record",
            ("ProgressContractError",),
            lambda record: record,
            "chat stream vector differs",
        ),
        ("progress.decode_line", ("ProgressContractError",), lambda _raw: {}, "chat stream line vector differs"),
    ],
)
def test_verifier_rejects_codec_vector_disagreement(tmp_path, target, error, returned, message):
    module, function = target.split(".")

    def reject_valid(modules):
        error_type = getattr(modules[module], error[0])

        def reject(*_args):
            raise error_type(*error[1:], "rejected")

        setattr(modules[module], function, reject)

    with pytest.raises(SystemExit, match=message):
        _execute(_copy(tmp_path / "raised"), patch=reject_valid)

    def return_wrong(modules):
        setattr(modules[module], function, returned)

    with pytest.raises(SystemExit, match=message):
        _execute(_copy(tmp_path / "returned"), patch=return_wrong)


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


def _refuse_vector_mutations(tmp_path: Path, *cases: tuple[str, Callable[[dict], None], str]) -> None:
    for name, mutate, message in cases:
        root = _copy(tmp_path / name)
        _vectors(root, mutate)
        with pytest.raises(SystemExit, match=message):
            _execute(root)


def test_verifier_rejects_missing_or_drifted_clarification_vectors(tmp_path):
    def missing(value):
        value["clarification"]["invalid"] = []

    def accepted_invalid(value):
        value["clarification"]["invalid"] = [value["clarification"]["valid"][0]]

    def rejected_valid(value):
        value["clarification"]["valid"] = [{**value["clarification"]["valid"][0], "extra": 1}]

    def drifted_rendering(value):
        value["clarification"]["rendered"][0] = "Something else"

    _refuse_vector_mutations(
        tmp_path,
        ("rendering", drifted_rendering, "a clarification rendering vector differs"),
        ("missing", missing, "clarification vectors are missing"),
        ("accepted", accepted_invalid, "an invalid clarification vector was admitted"),
        ("rejected", rejected_valid, "a valid clarification vector was not admitted exactly"),
    )


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

    _refuse_vector_mutations(
        tmp_path,
        ("missing", missing, "Team HTTP rendered copy vectors are missing"),
        ("accepted", accepted_invalid, "Team HTTP rendered copy negative vector differs"),
        ("rejected", rejected_valid, "Team HTTP rendered copy positive vector differs"),
    )


def test_verifier_rejects_missing_or_drifted_skill_vectors(tmp_path):
    def missing(value):
        value["skills"]["invalid"] = []

    def accepted_invalid(value):
        value["skills"]["invalid"] = [value["skills"]["valid"][1]]

    def rejected_valid(value):
        value["skills"]["valid"] = [[{"key": "procedure-000000000000", "contracts": {}, "steps": []}]]

    def drifted_apply(value):
        value["knowledge_apply"][0]["result"]["skills"] = []

    _refuse_vector_mutations(
        tmp_path,
        ("missing", missing, "skills vectors are missing"),
        ("accepted", accepted_invalid, "an invalid skills vector was admitted"),
        ("rejected", rejected_valid, "a valid skills vector was not admitted exactly"),
        ("apply", drifted_apply, "a knowledge application vector differs"),
    )


def test_verifier_rejects_missing_or_drifted_memory_vectors(tmp_path):
    def missing(value):
        value["memory"]["valid"] = []

    def accepted_invalid(value):
        value["memory_changes"]["invalid"] = [value["memory_changes"]["valid"][1]]

    def rejected_valid(value):
        value["memory"]["valid"] = [[{"topic": "Bad Topic", "preference": "x"}]]

    def drifted_apply(value):
        value["memory_apply"][0]["result"] = []

    _refuse_vector_mutations(
        tmp_path,
        ("missing", missing, "memory vectors are missing"),
        ("accepted", accepted_invalid, "an invalid memory_changes vector was admitted"),
        ("rejected", rejected_valid, "a valid memory vector was not admitted exactly"),
        ("apply", drifted_apply, "a memory application vector differs"),
    )


def test_verifier_rejects_missing_or_drifted_chat_conversation_vectors(tmp_path):
    def missing(value):
        value["chat_conversation"]["invalid"] = []

    def accepted_invalid(value):
        value["chat_conversation"]["invalid"] = [[]]

    def rejected_valid(value):
        value["chat_conversation"]["valid"] = [{"generated": "nine-entries"}]

    _refuse_vector_mutations(
        tmp_path,
        ("missing", missing, "conversation vectors are missing"),
        ("accepted", accepted_invalid, "conversation negative vector differs"),
        ("rejected", rejected_valid, "conversation positive vector differs"),
    )


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


def test_verifier_rejects_missing_or_drifted_recorded_routine_vectors(tmp_path):
    def proposal_name(value):
        value["routine_proposal"]["valid"][0]["name"] = "x" * 81

    cases = (
        (_set(("routine_position", "invalid"), []), "routine position vectors are missing"),
        (
            _set(("routine_position", "valid"), [{"value": {"phase": "replay", "step": 2}, "steps": 1}]),
            "a valid routine position vector was not admitted exactly",
        ),
        (
            _set(("routine_position", "invalid"), [{"value": {"phase": "replay", "step": 1}, "steps": 1}]),
            "an invalid routine position vector was admitted",
        ),
        (_set(("routine_proposal", "generated"), ["largest-unicode"]), "routine proposal vectors are missing"),
        (proposal_name, "a generated routine proposal vector differs at its bound"),
        (lambda v: v.pop("routine_refusal"), "routine_refusal vectors are missing"),
        (
            _set(("routine_listing", "valid"), [[{"output": {"mode": "decide"}}]]),
            "a valid routine_listing vector was not admitted exactly",
        ),
        (
            _set(("routine_proposal_answer", "invalid"), lambda v: [v["routine_proposal_answer"]["valid"][0]]),
            "an invalid routine_proposal_answer vector was admitted",
        ),
        (_set(("clarification_labels", "composed"), []), "clarification label vectors are missing"),
        (
            lambda v: v["clarification_labels"]["composed"][0].update({"message": "drift"}),
            "a composed clarification vector differs",
        ),
        (
            lambda v: v["clarification_labels"]["authored_segments"][0].update({"segments": []}),
            "an authored-segments vector differs",
        ),
        (_set(("routine_phrase", "team_asks"), []), "routine phrase vectors are missing"),
        (
            lambda v: v["routine_phrase"]["team_asks"][0].update(
                {"asks": not v["routine_phrase"]["team_asks"][0]["asks"]}
            ),
            "a routine phrase team_asks vector differs",
        ),
        (
            lambda v: v["routine_phrase"]["requests_routine"][0].update(
                {"requests": not v["routine_phrase"]["requests_routine"][0]["requests"]}
            ),
            "a routine phrase requests_routine vector differs",
        ),
        (
            lambda v: v["routine_phrase"]["outputs"][0].update({"outputs": ["drift"]}),
            "a routine phrase outputs vector differs",
        ),
    )
    for index, (mutate, message) in enumerate(cases):
        root = _copy(tmp_path / str(index))
        _vectors(root, mutate)
        with pytest.raises(SystemExit, match=message):
            _execute(root)


def _drop_locale(attribute: str):
    def patch(modules):
        value = dict(getattr(modules[attribute[0]], attribute[1]))
        value.pop("zh")
        setattr(modules[attribute[0]], attribute[1], value)

    return patch


def test_verifier_rejects_labels_replies_and_choices_that_miss_a_language(tmp_path):
    def english_fallback(modules):
        modules["routine_proposal"].answer_reply = lambda locale: modules["routine_proposal"].ANSWER_REPLIES["pt"]

    def repeated_choice(modules):
        choices = {locale: dict(labels) for locale, labels in modules["routine_proposal"].OUTPUT_CHOICES.items()}
        choices["en"]["none"] = choices["en"]["show"]
        modules["routine_proposal"].OUTPUT_CHOICES = choices

    cases = (
        (
            _drop_locale(("payload", "CLARIFICATION_LABELS")),
            "clarification labels do not cover every interface language",
        ),
        (
            _drop_locale(("routine_proposal", "ANSWER_REPLIES")),
            "Routine answer replies do not cover every interface language",
        ),
        (english_fallback, "does not get the English answer reply"),
        (_drop_locale(("routine_proposal", "OUTPUT_CHOICES")), "output choices do not name each output once"),
        (repeated_choice, "output choices do not name each output once"),
    )
    for index, (patch, message) in enumerate(cases):
        root = _copy(tmp_path / str(index))
        with pytest.raises(SystemExit, match=message):
            _execute(root, patch=patch)
