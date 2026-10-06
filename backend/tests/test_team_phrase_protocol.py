"""Store's mirror of Team's Routine phrase reader reads exactly Team's rules (ADR-0101)."""

from __future__ import annotations

import pytest

from app.protocol.http.v1 import phrase, routine

CARD = {
    "member": "note",
    "origin": "assistant",
    "value": "",
    "step": None,
    "pointer": None,
    "where": None,
    "item": None,
}


@pytest.mark.parametrize(
    ("text", "schedules"),
    [
        ("every day at 9 pm", ({"kind": "daily", "time": "21:00"},)),
        ("every day at 12am", ({"kind": "daily", "time": "00:00"},)),
        ("every day at 13pm", ()),
        ("every 2 seconds", ()),
    ],
)
def test_schedules_read_only_real_times_and_admitted_intervals(text, schedules):
    assert phrase.stated(text) == schedules


def test_a_repeated_output_or_zone_is_read_once():
    assert phrase.outputs("Mostrar o resultado sempre e mostrar o resultado sempre") == ("show",)
    assert phrase.zones("Europe/London e Europe/London") == ("Europe/London",)


@pytest.mark.parametrize("text", ["Europe/Atlantis", "America/" + "X" * 40 + "/Yyyy"])
def test_a_zone_that_does_not_load_or_is_not_canonical_is_not_read(text):
    assert phrase.zones(text) == ()


def test_a_card_input_with_an_unsafe_member_is_refused():
    assert routine._card_input({**CARD, "member": "bad\x00member"}, 1) is False
