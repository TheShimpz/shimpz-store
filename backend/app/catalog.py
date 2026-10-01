"""Strict projection of public Assistant metadata from Developers, in one interface language (ADR-0091)."""

from __future__ import annotations

import re

from app.protocol.http.v1 import payload as team_contract

MAX_ASSISTANTS = 1000
# Developers' machine contract, and Team and Brain after it, admit up to 128 Actions per Assistant.
MAX_ACTIONS = 128
_VERSION = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_CREATOR = re.compile(r"^@[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
_GITHUB = re.compile(
    r"^https://github\.com/[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?/"
    r"[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,98}[A-Za-z0-9])?$"
)
_ACTION_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
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
_ACTION_FIELDS = {"id", "integrations", "stored_inputs", "human_requests"}


class CatalogError(ValueError):
    """Developers returned catalog data outside the Store contract."""


def _text(value: object, maximum: int) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= maximum or any(ord(char) < 32 for char in value):
        raise CatalogError("catalog text is invalid")
    return value


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
        if (
            not isinstance(integration_id, str)
            or integration_id != provider
            or _ACTION_ID.fullmatch(integration_id) is None
        ):
            raise CatalogError("catalog Integration identity is invalid")
        projected.append({"id": integration_id, "provider": provider, "scopes": scopes})
    return projected


def _stored_inputs(value: object) -> frozenset[str]:
    """Validate the declared Stored Inputs; they are checked, not projected to the browser."""
    if not isinstance(value, list) or len(value) > 8:
        raise CatalogError("catalog Stored Inputs are invalid")
    identifiers = []
    for item in value:
        if (
            not isinstance(item, dict)
            or set(item) != {"id", "kind", "label", "description"}
            or not isinstance(item["id"], str)
            or len(item["id"]) > 64
            or _ACTION_ID.fullmatch(item["id"]) is None
            or item["kind"] != "password"
        ):
            raise CatalogError("catalog Stored Input is invalid")
        _text(item["label"], 80)
        _text(item["description"], 500)
        identifiers.append(item["id"])
    if len(set(identifiers)) != len(identifiers):
        raise CatalogError("catalog Stored Inputs are duplicated")
    return frozenset(identifiers)


def _actions(value: object, stored_inputs: frozenset[str]) -> list[dict[str, object]]:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_ACTIONS:
        raise CatalogError("catalog Actions are invalid")
    projected = []
    for item in value:
        if (
            not isinstance(item, dict)
            or set(item) != _ACTION_FIELDS
            or not isinstance(item["id"], str)
            or _ACTION_ID.fullmatch(item["id"]) is None
        ):
            raise CatalogError("catalog Action is invalid")
        human_requests = _closed_strings(item["human_requests"], 11, 25)
        if any(kind not in _HUMAN_REQUEST_KINDS for kind in human_requests):
            raise CatalogError("catalog Action human requests are invalid")
        if not set(_closed_strings(item["stored_inputs"], 1, 64)) <= stored_inputs:
            raise CatalogError("catalog Action Stored Inputs are invalid")
        projected.append(
            {
                "id": item["id"],
                "integrations": _closed_strings(item["integrations"], 16, 64),
                "human_requests": human_requests,
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
    if not isinstance(version, str) or _VERSION.fullmatch(version) is None:
        raise CatalogError("catalog Assistant version is invalid")
    if not isinstance(digest, str) or _DIGEST.fullmatch(digest) is None:
        raise CatalogError("catalog source digest is invalid")
    if not isinstance(icon_digest, str) or _DIGEST.fullmatch(icon_digest) is None:
        raise CatalogError("catalog icon digest is invalid")
    if platforms != ["linux/amd64", "linux/arm64"]:
        raise CatalogError("catalog platforms are invalid")
    if not isinstance(github, str) or _GITHUB.fullmatch(github) is None:
        raise CatalogError("catalog repository is invalid")
    return {
        "assistant_id": assistant_id,
        "name": _text(value["name"], 80),
        "summary": _text(value["summary"], 160),
        "assistant_version": version,
        "creators": _creators(value["creators"]),
        "github": github,
        "source_digest": digest,
        "icon_digest": icon_digest,
        "platforms": platforms,
        "allowed_hosts": _closed_strings(value["allowed_hosts"], 32, 253),
        "integrations": _integrations(value["integrations"]),
        "actions": _actions(value["actions"], _stored_inputs(value["stored_inputs"])),
    }


def project_catalog(value: object, locale: str) -> dict[str, object]:
    """Validate Developers' closed catalog for exactly the requested locale and return browser-safe metadata.

    Developers localizes only each summary, from the publication's own pack; a catalog in any other locale is refused
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
