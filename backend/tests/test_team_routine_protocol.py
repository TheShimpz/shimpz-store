"""Store's mirror of Team's Routine protocol admits exactly Team's golden vectors (ADR-0086, ADR-0101)."""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import pytest

from app.protocol.http.v1 import routine as routine_contract

VECTORS = json.loads((Path(routine_contract.__file__).parent / "vectors.json").read_text())
VIEWS = {
    "output": routine_contract.canonical_output,
    "routine": routine_contract.canonical_routine_view,
    "run": routine_contract.canonical_run_view,
    "notice_batch": routine_contract.canonical_notice_batch,
    "claim": routine_contract.canonical_claim,
    "claim_request": routine_contract.canonical_claim_request,
    "page": routine_contract.canonical_page,
    "summary": routine_contract.canonical_summary,
    "run_steps": routine_contract.canonical_run_steps,
    "incident": routine_contract.canonical_incident_view,
    "card": routine_contract.canonical_card,
    "card_answer_request": routine_contract.canonical_card_answer_request,
    "card_answer": routine_contract.canonical_card_answer,
    "segment_request": routine_contract.canonical_segment_request,
}
CARD = VECTORS["routine_proposal"]["valid"][0]


@pytest.mark.parametrize("kind", sorted(VIEWS))
def test_every_view_admits_exactly_its_vectors(kind):
    admit = VIEWS[kind]
    for value in VECTORS["routine_views"][kind]["valid"]:
        assert admit(value) == value
    for value in VECTORS["routine_views"][kind]["invalid"]:
        assert admit(value) is None
    assert admit(["not", "a", "view"]) is None


def test_notice_details_and_batches_are_closed():
    assert routine_contract.canonical_notice_detail("scope-changed", {"assistants": ["dns"]}) is not None
    plan = {
        "revision": 1,
        "plan_digest": "sha256:" + "d" * 64,
        "steps": 1,
        "actions": [["dns", "list-zones", 1]],
        "more": 0,
    }
    output = {"mode": "show", "step": 1, "when": None}
    created = {
        "name": "DNS",
        "plan": plan,
        "output": output,
        "schedule": {"kind": "daily", "time": "09:00"},
        "state": "active",
        "permitted": {"total": 1, "changes": 0},
        "model": None,
        "allowance": 0,
    }
    assert routine_contract.canonical_notice_detail("created", {**created, "timezone": "UTC", "timezone_source": "browser"}) is not None
    assert routine_contract.canonical_notice_detail("deleted", {}) == {}
    for outcome, detail in (
        ("scope-changed", {"assistants": []}),
        ("stopped", {"actions": [["dns", {"input": 1}]]}),
        ("stopped", {"actions": "dns"}),
        ("changed", {**created, "timezone": "UTC", "timezone_source": "browser", "input": {"zone": "x"}}),
        ("changed", {**created, "timezone": "UTC", "timezone_source": "browser", "plan": {**plan, "steps": 2}}),
    ):
        assert routine_contract.canonical_notice_detail(outcome, detail) is None
    assert routine_contract.canonical_notice_batch({"notices": ["x"], "more": False}) is None
    # A shown result's text is escaped by Team, and a disposition names a step by its position (ADR-0092, 2026-10-05).
    assert routine_contract.escaped("a\u202eb") == "a\\u202eb"
    assert routine_contract.canonical_disposition({"mode": "show", "step": 2, "when": None}, 1) is None
    assert routine_contract.canonical_disposition({"mode": "decide", "step": None, "when": "always"}, 0) is not None
    assert routine_contract.canonical_disposition([], 1) is None


def test_the_recorded_card_and_its_answers_are_closed():
    for kind, admit in (
        ("routine_proposal", routine_contract.canonical_proposal),
        ("routine_refusal", routine_contract.canonical_refusal),
        ("routine_proposal_answer", routine_contract.canonical_proposal_answer),
        ("routine_decision_record", routine_contract.canonical_decision_record),
        ("routine_run_usage", routine_contract.canonical_run_usage),
    ):
        for value in VECTORS[kind]["valid"]:
            assert admit(value) == value
        for value in VECTORS[kind]["invalid"]:
            assert admit(value) is None
    assert not routine_contract._decision([])
    assert not routine_contract._card_input([], 1)
    assert not routine_contract._card_input({**CARD["steps"][1]["inputs"][0], "origin": "guess"}, 2)
    assert not routine_contract._card_permitted({})
    assert not routine_contract._card_permitted([{**CARD["permitted"][0], "read_only": 1}])
    assert routine_contract.where_text("a\u202eb") == '"a\\u202eb"'
    assert routine_contract.where_text(7) == "7"
    for value in VECTORS["routine_position"]["valid"]:
        assert routine_contract.canonical_position(value["value"], value["steps"]) == value["value"]
    for value in VECTORS["routine_position"]["invalid"]:
        assert routine_contract.canonical_position(value["value"], value["steps"]) is None


def test_run_diagnostics_admit_exactly_the_golden_vectors():
    for value in VECTORS["routine_diagnostics"]["valid"]:
        assert routine_contract.canonical_diagnostics(value) == value
    for value in VECTORS["routine_diagnostics"]["invalid"]:
        assert routine_contract.canonical_diagnostics(value) is None
    assert routine_contract.canonical_failure([]) is None
    assert routine_contract.canonical_diagnostic([]) is None
    assert not routine_contract._diagnostic_text("lone \ud800 surrogate")
    assert not routine_contract._diagnostic_text(7)


def test_the_plan_projection_is_closed_and_its_previews_bounded():
    assert routine_contract.literal_preview({"a": "x‮"}) == '{"a":"x\\u202e"}'
    assert len(routine_contract.literal_preview("y" * 300)) == routine_contract.MAX_PREVIEW_CHARS
    step = {
        "position": 1,
        "assistant": "dns",
        "action": "list-zones",
        "read_only": True,
        "inputs": [],
        "stored_inputs": [],
    }
    assert routine_contract.canonical_step(step, 1) == step
    for value, position in (
        ("x", 1),
        (step, 2),
        ({**step, "inputs": ["x"]}, 1),
        ({**step, "inputs": [{"member": "", "source": "literal", "value": "1"}]}, 1),
    ):
        assert routine_contract.canonical_step(value, position) is None


def test_every_schedule_has_a_whole_rolling_cap_and_one_run_mode():
    for vector in VECTORS["routine_schedule"]["daily_rate"]:
        schedule = vector["schedule"]
        assert routine_contract.daily_cap(schedule) == -(-Fraction(vector["rate"]) // 1)
        expected = "continuous" if schedule["kind"] == "continuous" else "scheduled"
        assert routine_contract.run_mode(schedule) == expected
        assert expected in routine_contract.RUN_MODES


def test_a_runs_active_time_grows_with_its_units_up_to_its_ceiling():
    assert routine_contract.active_seconds(8) == routine_contract.SHORT_ACTIVE_SECONDS
    assert routine_contract.active_seconds(256) == routine_contract.MAX_ACTIVE_SECONDS
