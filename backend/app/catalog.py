"""Strict projection of public Assistant metadata from Developers."""

from __future__ import annotations

import re

from app.protocol.http.v1 import payload as team_contract

MAX_ASSISTANTS = 1000
_VERSION = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_CREATOR = re.compile(r"^@[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
_GITHUB = re.compile(
    r"^https://github\.com/[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?/"
    r"[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,98}[A-Za-z0-9])?$"
)
_POWER_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_ASSISTANT_FIELDS = {
    "assistant_id",
    "name",
    "summary",
    "assistant_version",
    "creators",
    "github",
    "source_digest",
    "platforms",
    "allowed_hosts",
    "accounts",
    "powers",
}


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


def _accounts(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list) or len(value) > 16:
        raise CatalogError("catalog accounts are invalid")
    projected = []
    for item in value:
        if not isinstance(item, dict) or set(item) != {"id", "provider", "scopes"}:
            raise CatalogError("catalog Account is invalid")
        account_id = item["id"]
        provider = item["provider"]
        scopes = _closed_strings(item["scopes"], 32, 128)
        if not isinstance(account_id, str) or account_id != provider or _POWER_ID.fullmatch(account_id) is None:
            raise CatalogError("catalog Account identity is invalid")
        projected.append({"id": account_id, "provider": provider, "scopes": scopes})
    return projected


def _powers(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list) or not 1 <= len(value) <= 64:
        raise CatalogError("catalog Powers are invalid")
    projected = []
    for item in value:
        if (
            not isinstance(item, dict)
            or set(item) != {"id", "input_schema", "output_schema", "accounts"}
            or not isinstance(item["id"], str)
            or _POWER_ID.fullmatch(item["id"]) is None
            or not isinstance(item["input_schema"], dict)
            or not isinstance(item["output_schema"], dict)
        ):
            raise CatalogError("catalog Power is invalid")
        projected.append(
            {
                "id": item["id"],
                "accounts": _closed_strings(item["accounts"], 16, 64),
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
    platforms = value["platforms"]
    github = value["github"]
    if not isinstance(version, str) or _VERSION.fullmatch(version) is None:
        raise CatalogError("catalog Assistant version is invalid")
    if not isinstance(digest, str) or _DIGEST.fullmatch(digest) is None:
        raise CatalogError("catalog source digest is invalid")
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
        "platforms": platforms,
        "allowed_hosts": _closed_strings(value["allowed_hosts"], 32, 253),
        "accounts": _accounts(value["accounts"]),
        "powers": _powers(value["powers"]),
    }


def project_catalog(value: object) -> dict[str, object]:
    """Validate Developers' closed catalog and return browser-safe metadata."""
    if not isinstance(value, dict) or set(value) != {"version", "assistants"} or value["version"] != 1:
        raise CatalogError("catalog envelope is invalid")
    assistants = value["assistants"]
    if not isinstance(assistants, list) or len(assistants) > MAX_ASSISTANTS:
        raise CatalogError("catalog size is invalid")
    projected = [_assistant(item) for item in assistants]
    identities = [item["assistant_id"] for item in projected]
    if identities != sorted(identities) or len(set(identities)) != len(identities):
        raise CatalogError("catalog Assistant ordering is invalid")
    return {"version": 1, "assistants": projected}
