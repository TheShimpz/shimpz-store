"""Write the Python catalog tests' projection cases and the Python Store's answers for the same-named Rust tests.

Run with the Store's own Python environment, from the umbrella root (tooling until the Python is deleted):

    uv run --project store/backend --frozen python store/backend/oracle/catalog_vectors.py

Each entry of `src/catalog/project/vectors.json` names the Python test it comes from, the Developers document, the
requested locale, and the projected bytes `project_catalog` serializes to, or null when it refuses the document.
"""

import copy
import importlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# The Store's own package, importable only once its root is on the path.
catalog = importlib.import_module("app.catalog")

_SPEC = importlib.util.spec_from_file_location("catalog_tests", ROOT / "tests" / "test_assistant_catalog.py")
TESTS = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(TESTS)
_assistant, _catalog = TESTS._assistant, TESTS._catalog
HELP_URL, LONGEST_HOST = TESTS.HELP_URL, TESTS.LONGEST_HOST


def _answer(value, locale) -> str | None:
    try:
        projected = catalog.project_catalog(copy.deepcopy(value), locale)
    except catalog.CatalogError:
        return None
    return json.dumps(projected, separators=(",", ":"), sort_keys=True, ensure_ascii=False)


def _entry(test: str, value, locale: str = "en") -> dict:
    return {
        "test": test,
        "document": json.dumps(value, ensure_ascii=False),
        "locale": locale,
        "python": _answer(value, locale),
    }


def _parameters(test) -> list:
    return next(mark.args[1] for mark in test.pytestmark if mark.name == "parametrize")


def _refusals() -> list[dict]:
    entries = []
    for mutate in _parameters(TESTS.test_rejects_ambiguous_or_executable_catalog_data):
        value = _catalog(_assistant())
        mutate(value)
        entries.append(_entry("rejects_ambiguous_or_executable_catalog_data", value))
    return entries


def _links() -> list[dict]:
    links = {
        "instagram": "https://www.instagram.com/shimpz",
        "linkedin": "https://www.linkedin.com/company/shimpz",
        "youtube": "https://www.youtube.com/@shimpz",
        "x": "https://x.com/shimpz",
        "github": "https://github.com/TheShimpz",
        "site": "https://hello.example.org/docs?tab=about",
    }
    bare = {
        "youtube": "https://youtube.com/@shimpz",
        "linkedin": "https://linkedin.com/in/shimpz",
        "instagram": "https://instagram.com/shimpz",
        "site": "https://hello.example.org/" + "a" * 230,
    }
    name = "admits_every_link_kind_on_its_host_in_canonical_order"
    return [_entry(name, _catalog(_assistant(links=chosen))) for chosen in (links, bare, {})]


def _hosts() -> list[dict]:
    hosts = [LONGEST_HOST, "a.co", "api-2.example.com", "9to5.example.org"] + [
        f"api-{index:02}.example.com" for index in range(28)
    ]
    name = "admits_every_allowed_host_shape_developers_emits"
    return [_entry(name, _catalog(_assistant(allowed_hosts=chosen))) for chosen in (hosts, [])]


def _localized() -> list[dict]:
    assistant = _assistant(
        description="D" * 499 + "é",
        stored_inputs=[
            {"id": "api-token", "kind": "password", "label": "ç" * 120, "description": "d" * 500, "help_url": HELP_URL}
        ],
    )
    assistant["actions"][0].update(effect="mutating", description="á" * 120)
    return [_entry("admits_localized_display_copy_up_to_its_catalog_bounds", _catalog(assistant, locale="pt"), "pt")]


def _locales() -> list[dict]:
    entries = [
        _entry(
            "projects_exactly_the_requested_locale",
            _catalog(_assistant(summary=f"Summary ({locale})."), locale=locale),
            locale,
        )
        for locale in _parameters(TESTS.test_projects_exactly_the_requested_locale)
    ]
    entries += [
        _entry("refuses_a_locale_outside_the_closed_set", _catalog(_assistant(), locale=requested), requested)
        for requested in _parameters(TESTS.test_refuses_a_locale_outside_the_closed_set)
        if requested is not None
    ]
    return entries


def _actions() -> list[dict]:
    action = _assistant()["actions"][0]
    name = "an_assistant_with_the_producer_maximum_of_actions_is_projected"
    entries = [
        _entry(name, _catalog(_assistant(actions=[{**action, "id": f"action-{index}"} for index in range(count)])))
        for count in (128, 129)
    ]
    integrations = [
        {"id": f"provider-{index:02}", "provider": f"provider-{index:02}", "scopes": [f"scope:{n}" for n in range(32)]}
        for index in range(16)
    ]
    inputs = [f"input:{kind}" for kind in ("text", "textarea", "password", "phone", "select", "choice", "choices")]
    shaped = {**action, "integrations": [item["id"] for item in integrations[:4]]}
    actions = [
        {**shaped, "id": "zeta", "human_requests": [*inputs, "auth:passkey"]},
        {**shaped, "id": "alpha", "human_requests": ["approval"]},
    ]
    shapes = _assistant(integrations=integrations, actions=actions)
    entries.append(_entry("every_integration_and_action_shape_developers_emits_is_projected", _catalog(shapes)))
    keys = [
        {"id": f"key-{index}", "kind": "password", "label": "Key", "description": "Key.", "help_url": HELP_URL}
        for index in range(8)
    ]
    names = [key["id"] for key in keys]
    for listed in (names, [*names, "key-8"]):
        assistant = _assistant(stored_inputs=keys)
        assistant["actions"][0]["stored_inputs"] = listed
        entries.append(_entry("an_action_may_use_several_declared_stored_inputs", _catalog(assistant)))
    return entries


def _texts() -> list[dict]:
    name = "the_summary_is_a_short_description_of_at_most_eighty_characters"
    entries = [
        _entry(name, _catalog(_assistant(summary=summary))) for summary in ("s" * 80, "s" * 79 + "\U0001f44b", "s" * 81)
    ]
    entries.append(_entry("projects_only_bounded_browser_metadata", _catalog(_assistant())))
    return entries


def _identifiers() -> list[dict]:
    name = "the_public_catalog_admits_developers_identifiers"
    action = {
        "id": "a" * 64,
        "integrations": [],
        "stored_inputs": [],
        "human_requests": [],
        "effect": "read_only",
        "description": "Read records.",
    }
    integration = {"id": "p" * 64, "provider": "p" * 64, "scopes": ["read"]}
    stored = {
        "id": "s" * 64,
        "kind": "password",
        "label": "Key",
        "description": "The API key.",
        "help_url": "https://dashboard.exa.ai/api-keys",
    }
    variants = [
        (action, integration, stored),
        ({**action, "id": "a" * 65}, integration, stored),
        ({**action, "id": "dns.read"}, integration, stored),
        (action, {**integration, "id": "p" * 65, "provider": "p" * 65}, stored),
        (action, integration, {**stored, "id": "s.key"}),
    ]
    return [
        _entry(name, _catalog(_assistant(actions=[chosen], integrations=[provider], stored_inputs=[key])))
        for chosen, provider, key in variants
    ]


def main() -> int:
    entries = [*_refusals(), *_links(), *_hosts(), *_localized(), *_locales(), *_actions(), *_texts(), *_identifiers()]
    path = ROOT / "src" / "catalog" / "project" / "vectors.json"
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    print(f"{len(entries)} catalog vectors, {sum(entry['python'] is None for entry in entries)} refused")
    return 0


if __name__ == "__main__":
    sys.exit(main())
