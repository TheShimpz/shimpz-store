"""Store admits every Team and Developers identifier by its own kind, as the producing protocol defines it."""

from __future__ import annotations

import pytest

from app import catalog
from app.chat import events


def test_a_human_challenge_names_any_canonical_action() -> None:
    for action in ("dns.read", "zone_get", "a" * 128):
        assert events._human_identity({"id": action, "summary": "Read"}, "summary", 160) == {
            "id": action,
            "summary": "Read",
        }
    for action in ("a" * 129, "dns..read", "Lookup"):
        assert events._human_identity({"id": action, "summary": "Read"}, "summary", 160) is None


def test_the_public_catalog_admits_developers_identifiers() -> None:
    action = {"id": "a" * 64, "integrations": [], "stored_inputs": [], "human_requests": []}
    assert catalog._actions([action], frozenset())[0]["id"] == "a" * 64
    for action_id in ("a" * 65, "dns.read"):
        with pytest.raises(catalog.CatalogError):
            catalog._actions([{**action, "id": action_id}], frozenset())
    integration = {"id": "p" * 64, "provider": "p" * 64, "scopes": ["read"]}
    assert catalog._integrations([integration])[0]["id"] == "p" * 64
    with pytest.raises(catalog.CatalogError):
        catalog._integrations([{**integration, "id": "p" * 65, "provider": "p" * 65}])
    stored_input = {"id": "s" * 64, "kind": "password", "label": "Key", "description": "The API key."}
    assert catalog._stored_inputs([stored_input]) == frozenset({"s" * 64})
    with pytest.raises(catalog.CatalogError):
        catalog._stored_inputs([{**stored_input, "id": "s.key"}])
