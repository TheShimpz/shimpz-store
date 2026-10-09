"""Strict projection of public Assistant metadata from Developers, in one interface language (ADR-0091).

Developers localizes the display copy (summary, description, Action descriptions, and Stored Input labels) from each
publication's own language pack; Creator links are unverified, presentation-only https URLs on their kind's host.
"""

import re

from app.protocol.http.v1 import payload as team_contract

MAX_ASSISTANTS = 1000
# Developers' machine contract, and Team and Brain after it, admit up to 128 Actions per Assistant.
MAX_ACTIONS = 128
VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_CREATOR = re.compile(r"^@[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
_GITHUB = re.compile(
    r"^https://github\.com/[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?/"
    r"[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,98}[A-Za-z0-9])?$"
)
_HUMAN_REQUEST_KINDS = {
    "approval",
    "input:text",
    "input:textarea",
    "input:password",
    "input:phone",
    "input:select",
    "input:choice",
    "input:choices",
    "auth:password",
    "auth:totp",
    "auth:passkey",
}
_ASSISTANT_FIELDS = {
    "assistant_id",
    "name",
    "summary",
    "description",
    "links",
    "assistant_version",
    "creators",
    "github",
    "icon_digest",
    "source_digest",
    "platforms",
    "allowed_hosts",
    "integrations",
    "stored_inputs",
    "actions",
}
# Developers' catalog carries schema-free Action metadata; complete schemas stay in exact resolution.
_ACTION_FIELDS = {"id", "integrations", "stored_inputs", "human_requests", "effect", "description"}
# A tuple, so an unhashable producer value compares unequal instead of raising.
_ACTION_EFFECTS = ("read_only", "mutating")
# Localized display copy bounds: the Assistant description and one line (Action description, Stored Input label).
DESCRIPTION_BOUND = 500
LINE_BOUND = 120
MAX_LINK_CHARS = 256
# Creator links in canonical display order, each with the exact https origins its kind admits; `site` admits any
# public host the help-URL grammar admits.
_LINK_PREFIXES: dict[str, tuple[str, ...]] = {
    "site": ("https://",),
    "github": ("https://github.com/",),
    "x": ("https://x.com/",),
    "youtube": ("https://youtube.com/", "https://www.youtube.com/"),
    "linkedin": ("https://linkedin.com/", "https://www.linkedin.com/"),
    "instagram": ("https://instagram.com/", "https://www.instagram.com/"),
}


class CatalogError(ValueError):
    """Developers returned catalog data outside the Store contract."""


def _text(value: object, maximum: int) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= maximum or any(ord(char) < 32 for char in value):
        raise CatalogError("catalog text is invalid")
    return value


def _display(value: object, maximum: int) -> str:
    """One localized display text: bounded, trimmed, and free of C0, DEL, and C1 controls."""
    text = _text(value, maximum)
    if text.strip() != text or any(0x7F <= ord(char) <= 0x9F for char in text):
        raise CatalogError("catalog display text is invalid")
    return text


def _links(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or not set(value) <= set(_LINK_PREFIXES):
        raise CatalogError("catalog links are invalid")
    for kind, url in value.items():
        if (
            not isinstance(url, str)
            or len(url) > MAX_LINK_CHARS
            or team_contract.canonical_help_url(url) is None
            or not url.startswith(_LINK_PREFIXES[kind])
        ):
            raise CatalogError("catalog link is invalid")
    return {kind: value[kind] for kind in _LINK_PREFIXES if kind in value}


def _closed_strings(value: object, maximum: int, item_maximum: int) -> list[str]:
    if (
        not isinstance(value, list)
        or len(value) > maximum
        or not all(isinstance(item, str) and 1 <= len(item) <= item_maximum for item in value)
        or len(set(value)) != len(value)
    ):
        raise CatalogError("catalog string collection is invalid")
    return value


def _creators(value: object) -> list[str]:
    creators = _closed_strings(value, 16, 39)
    if not creators or any(_CREATOR.fullmatch(creator) is None for creator in creators):
        raise CatalogError("catalog creators are invalid")
    return creators


def _integrations(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list) or len(value) > 16:
        raise CatalogError("catalog integrations are invalid")
    projected = []
    for item in value:
        if not isinstance(item, dict) or set(item) != {"id", "provider", "scopes"}:
            raise CatalogError("catalog Integration is invalid")
        integration_id = item["id"]
        provider = item["provider"]
        scopes = _closed_strings(item["scopes"], 32, 128)
        if team_contract.canonical_identifier(integration_id) is None or integration_id != provider:
            raise CatalogError("catalog Integration identity is invalid")
        projected.append({"id": integration_id, "provider": provider, "scopes": scopes})
    return projected


def _stored_inputs(value: object) -> list[dict[str, str]]:
    """Validate the declared Stored Inputs and project only each identifier and localized label."""
    if not isinstance(value, list) or len(value) > 8:
        raise CatalogError("catalog Stored Inputs are invalid")
    projected = []
    for item in value:
        if (
            not isinstance(item, dict)
            or set(item) != {"id", "kind", "label", "description"}
            or team_contract.canonical_identifier(item["id"]) is None
            or item["kind"] != "password"
        ):
            raise CatalogError("catalog Stored Input is invalid")
        # The label is localized display copy; the description stays canonical English and is not projected.
        label = _display(item["label"], LINE_BOUND)
        _text(item["description"], 500)
        projected.append({"id": item["id"], "label": label})
    if len({item["id"] for item in projected}) != len(projected):
        raise CatalogError("catalog Stored Inputs are duplicated")
    return projected


def _actions(value: object, stored_inputs: frozenset[str]) -> list[dict[str, object]]:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_ACTIONS:
        raise CatalogError("catalog Actions are invalid")
    projected = []
    for item in value:
        if (
            not isinstance(item, dict)
            or set(item) != _ACTION_FIELDS
            or team_contract.canonical_identifier(item["id"]) is None
            or item["effect"] not in _ACTION_EFFECTS
        ):
            raise CatalogError("catalog Action is invalid")
        human_requests = _closed_strings(item["human_requests"], 11, 25)
        if any(kind not in _HUMAN_REQUEST_KINDS for kind in human_requests):
            raise CatalogError("catalog Action human requests are invalid")
        # An Action may use any of its Assistant's declared Stored Inputs, at most eight (ADR-0059).
        if not set(_closed_strings(item["stored_inputs"], 8, 64)) <= stored_inputs:
            raise CatalogError("catalog Action Stored Inputs are invalid")
        projected.append(
            {
                "id": item["id"],
                "integrations": _closed_strings(item["integrations"], 16, 64),
                "human_requests": human_requests,
                "effect": item["effect"],
                "description": _display(item["description"], LINE_BOUND),
            }
        )
    return projected


def _assistant(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != _ASSISTANT_FIELDS:
        raise CatalogError("catalog Assistant fields are invalid")
    assistant_id = team_contract.canonical_assistant_id(value["assistant_id"])
    if assistant_id is None:
        raise CatalogError("catalog Assistant identifier is invalid")
    version = value["assistant_version"]
    digest = value["source_digest"]
    icon_digest = value["icon_digest"]
    platforms = value["platforms"]
    github = value["github"]
    if not isinstance(version, str) or VERSION_RE.fullmatch(version) is None:
        raise CatalogError("catalog Assistant version is invalid")
    if not isinstance(digest, str) or team_contract.SOURCE_DIGEST_RE.fullmatch(digest) is None:
        raise CatalogError("catalog source digest is invalid")
    if not isinstance(icon_digest, str) or team_contract.SOURCE_DIGEST_RE.fullmatch(icon_digest) is None:
        raise CatalogError("catalog icon digest is invalid")
    if platforms != ["linux/amd64", "linux/arm64"]:
        raise CatalogError("catalog platforms are invalid")
    if not isinstance(github, str) or _GITHUB.fullmatch(github) is None:
        raise CatalogError("catalog repository is invalid")
    stored_inputs = _stored_inputs(value["stored_inputs"])
    return {
        "assistant_id": assistant_id,
        "name": _text(value["name"], 80),
        "summary": _text(value["summary"], 80),
        "description": _display(value["description"], DESCRIPTION_BOUND),
        "links": _links(value["links"]),
        "assistant_version": version,
        "creators": _creators(value["creators"]),
        "github": github,
        "source_digest": digest,
        "icon_digest": icon_digest,
        "platforms": platforms,
        "allowed_hosts": _closed_strings(value["allowed_hosts"], 32, 253),
        "integrations": _integrations(value["integrations"]),
        "stored_inputs": stored_inputs,
        "actions": _actions(value["actions"], frozenset(item["id"] for item in stored_inputs)),
    }


def project_catalog(value: object, locale: str) -> dict[str, object]:
    """Validate Developers' closed catalog for exactly the requested locale and return browser-safe metadata.

    Developers localizes each publication's display copy from its own pack; a catalog in any other locale is refused
    so a cache can never serve one language's copy under another.
    """
    if (
        not isinstance(value, dict)
        or set(value) != {"version", "locale", "assistants"}
        or value["version"] != 1
        or team_contract.canonical_locale(locale) is None
        or value["locale"] != locale
    ):
        raise CatalogError("catalog envelope is invalid")
    assistants = value["assistants"]
    if not isinstance(assistants, list) or len(assistants) > MAX_ASSISTANTS:
        raise CatalogError("catalog size is invalid")
    projected = [_assistant(item) for item in assistants]
    identities = [item["assistant_id"] for item in projected]
    if identities != sorted(identities) or len(set(identities)) != len(identities):
        raise CatalogError("catalog Assistant ordering is invalid")
    return {"version": 1, "locale": locale, "assistants": projected}
