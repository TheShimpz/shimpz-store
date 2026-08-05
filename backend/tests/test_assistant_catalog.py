"""Public Store projection of Developers-owned Assistant metadata."""

from __future__ import annotations

import copy
import hashlib

import pytest
from app import catalog
from app.main import app
from app.routers import public
from fastapi.testclient import TestClient

DIGEST = "sha256:" + ("a" * 64)
ICON_DIGEST = "sha256:" + ("b" * 64)


def _assistant(**changes) -> dict[str, object]:
    value = {
        "assistant_id": "hello-world",
        "name": "Hello World",
        "summary": "Greets the Team.",
        "assistant_version": "10.0.0",
        "creators": ["@shimpz"],
        "github": "https://github.com/TheShimpz/hello-world",
        "source_digest": DIGEST,
        "icon_digest": ICON_DIGEST,
        "platforms": ["linux/amd64", "linux/arm64"],
        "allowed_hosts": ["api.example.com"],
        "integrations": [{"id": "github", "provider": "github", "scopes": ["repo:read"]}],
        "powers": [
            {
                "id": "hello",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "integrations": ["github"],
            }
        ],
    }
    value.update(changes)
    return value


def test_projects_only_bounded_browser_metadata() -> None:
    projected = catalog.project_catalog({"version": 1, "assistants": [_assistant()]})

    assert projected == {
        "version": 1,
        "assistants": [
            {
                "assistant_id": "hello-world",
                "name": "Hello World",
                "summary": "Greets the Team.",
                "assistant_version": "10.0.0",
                "creators": ["@shimpz"],
                "github": "https://github.com/TheShimpz/hello-world",
                "source_digest": DIGEST,
                "icon_digest": ICON_DIGEST,
                "platforms": ["linux/amd64", "linux/arm64"],
                "allowed_hosts": ["api.example.com"],
                "integrations": [{"id": "github", "provider": "github", "scopes": ["repo:read"]}],
                "powers": [{"id": "hello", "integrations": ["github"]}],
            }
        ],
    }
    serialized = str(projected)
    assert "image_reference" not in serialized
    assert "input_schema" not in serialized


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(extra=True),
        lambda value: value["assistants"][0].update(source_digest="sha256:bad"),
        lambda value: value["assistants"][0].update(platforms=["linux/amd64"]),
        lambda value: value["assistants"].append(copy.deepcopy(value["assistants"][0])),
        lambda value: value["assistants"][0]["powers"][0].update(command="/bin/sh"),
    ],
)
def test_rejects_ambiguous_or_executable_catalog_data(mutate) -> None:
    value = {"version": 1, "assistants": [_assistant()]}
    mutate(value)

    with pytest.raises(catalog.CatalogError):
        catalog.project_catalog(value)


def test_public_route_caches_only_a_valid_developers_catalog(monkeypatch) -> None:
    async def valid_catalog(*_args, **_kwargs):
        return 200, {"version": 1, "assistants": [_assistant()]}

    monkeypatch.setattr(public, "call_bounded", valid_catalog)
    with TestClient(app) as client:
        response = client.get("/api/assistants")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=60, s-maxage=300"
    assert response.json()["assistants"][0]["source_digest"] == DIGEST


def test_public_icon_route_verifies_and_immutably_caches_exact_bytes(monkeypatch) -> None:
    contents = b"canonical icon"
    icon_hash = hashlib.sha256(contents).hexdigest()

    async def valid_icon(*_args, **_kwargs):
        return 200, contents

    monkeypatch.setattr(public, "call_asset_bounded", valid_icon)
    with TestClient(app) as client:
        response = client.get(f"/api/assistant-icons/{'a' * 64}/{icon_hash}.png")

    assert response.status_code == 200
    assert response.content == contents
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_public_icon_route_fails_closed_on_digest_mismatch(monkeypatch) -> None:
    async def invalid_icon(*_args, **_kwargs):
        return 200, b"wrong icon"

    monkeypatch.setattr(public, "call_asset_bounded", invalid_icon)
    with TestClient(app) as client:
        response = client.get(f"/api/assistant-icons/{'a' * 64}/{'b' * 64}.png")

    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("upstream", [(502, {}), (200, {"version": 1, "assistants": "bad"})])
def test_public_route_fails_closed_without_cache(monkeypatch, upstream) -> None:
    async def invalid_catalog(*_args, **_kwargs):
        return upstream

    monkeypatch.setattr(public, "call_bounded", invalid_catalog)
    with TestClient(app) as client:
        response = client.get("/api/assistants")

    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {"detail": "Assistant catalog is unavailable"}
