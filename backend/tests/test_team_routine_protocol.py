"""Store's mirror of Team's Routine protocol admits exactly Team's golden vectors (ADR-0086)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.protocol.http.v1 import routine as routine_contract

VECTORS = json.loads((Path(routine_contract.__file__).parent / "vectors.json").read_text())
VIEWS = {
    "proposal": routine_contract.canonical_proposal,
    "preview": routine_contract.canonical_preview,
    "routine": routine_contract.canonical_routine_view,
    "run": routine_contract.canonical_run_view,
    "notice_batch": routine_contract.canonical_notice_batch,
    "claim": routine_contract.canonical_claim,
    "claim_request": routine_contract.canonical_claim_request,
}


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
    for outcome, detail in (
        ("scope-changed", {"assistants": []}),
        ("stopped", {"actions": [["dns", {"input": 1}]]}),
        ("stopped", {"actions": "dns"}),
    ):
        assert routine_contract.canonical_notice_detail(outcome, detail) is None
    assert routine_contract.canonical_notice_batch({"notices": ["x"], "more": False}) is None


def test_run_diagnostics_admit_exactly_the_golden_vectors():
    for value in VECTORS["routine_diagnostics"]["valid"]:
        assert routine_contract.canonical_diagnostics(value) == value
    for value in VECTORS["routine_diagnostics"]["invalid"]:
        assert routine_contract.canonical_diagnostics(value) is None
    assert routine_contract.canonical_failure([]) is None
    assert routine_contract.canonical_diagnostic([]) is None
    assert not routine_contract._diagnostic_text("lone \ud800 surrogate")
    assert not routine_contract._diagnostic_text(7)
