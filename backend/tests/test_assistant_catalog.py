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
    """One entry in the exact shape Developers publishes (developers-api resolve.rs catalog value)."""
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
        "stored_inputs": [
            {"id": "api-token", "kind": "password", "label": "API token", "description": "Used to call the API."}
        ],
        "actions": [
            {
                "id": "hello",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "integrations": ["github"],
                "stored_inputs": ["api-token"],
                "human_requests": ["approval", "input:text"],
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
                "actions": [
                    {
                        "id": "hello",
                        "integrations": ["github"],
                        "human_requests": ["approval", "input:text"],
                    }
                ],
            }
        ],
    }
    serialized = str(projected)
    assert "image_reference" not in serialized
    assert "input_schema" not in serialized
    # Stored Input declarations are validated but never projected to the browser.
    assert "stored_inputs" not in serialized


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(extra=True),
        lambda value: value["assistants"][0].update(name="bad\nname"),
        lambda value: value["assistants"][0].update(creators=[]),
        lambda value: value["assistants"][0].update(integrations="invalid"),
        lambda value: value["assistants"][0].update(integrations=[{"id": "github"}]),
        lambda value: value["assistants"][0].update(
            integrations=[{"id": "github", "provider": "gitlab", "scopes": []}]
        ),
        lambda value: value["assistants"][0].update(actions=[]),
        lambda value: value["assistants"][0].update(extra="field"),
        lambda value: value["assistants"][0].update(assistant_id="Invalid"),
        lambda value: value["assistants"][0].update(assistant_version="01.0.0"),
        lambda value: value["assistants"][0].update(source_digest="sha256:bad"),
        lambda value: value["assistants"][0].update(icon_digest="sha256:bad"),
        lambda value: value["assistants"][0].update(platforms=["linux/amd64"]),
        lambda value: value["assistants"][0].update(github="https://example.com/repository"),
        lambda value: value["assistants"].append(copy.deepcopy(value["assistants"][0])),
        lambda value: value["assistants"][0]["actions"][0].update(command="/bin/sh"),
        lambda value: value["assistants"][0]["actions"][0].update(human_requests=["unknown"]),
        lambda value: value["assistants"][0]["actions"][0].update(human_requests=["approval", "approval"]),
        lambda value: value["assistants"][0].pop("stored_inputs"),
        lambda value: value["assistants"][0]["actions"][0].pop("stored_inputs"),
        lambda value: value["assistants"][0].update(stored_inputs="invalid"),
        lambda value: value["assistants"][0]["stored_inputs"][0].update(kind="text"),
        lambda value: value["assistants"][0]["stored_inputs"][0].update(label="bad\nlabel"),
        lambda value: value["assistants"][0]["stored_inputs"][0].update(extra=True),
        lambda value: value["assistants"][0]["stored_inputs"].append(dict(value["assistants"][0]["stored_inputs"][0])),
        lambda value: value["assistants"][0].update(
            stored_inputs=[
                {"id": f"key-{index}", "kind": "password", "label": "Key", "description": "Key."} for index in range(9)
            ]
        ),
        lambda value: value["assistants"][0]["actions"][0].update(stored_inputs=["undeclared"]),
        lambda value: value["assistants"][0]["actions"][0].update(stored_inputs=["api-token", "api-token"]),
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


# Admin's byte cap for the Store catalog response (admin/backend/chat/store_catalog.py).
ADMIN_CATALOG_BYTE_LIMIT = 4 * 1024 * 1024


def test_a_full_utf8_catalog_is_served_as_utf8_within_the_consumer_byte_limit(monkeypatch) -> None:
    """The response keeps multibyte text as UTF-8; escaping it would push a valid full catalog past Admin's cap."""
    name = "Á" * 80
    summary = "É" * 160

    def entry(index: int) -> dict[str, object]:
        # Long public texts make a full catalog near the consumer cap, as real publications can be.
        return _assistant(
            assistant_id=f"assistant-{index:04d}",
            name=name,
            summary=summary,
            allowed_hosts=[f"{'á' * 60}{host:02d}.example.com" for host in range(16)],
        )

    upstream_value = {"version": 1, "assistants": [entry(index) for index in range(1000)]}

    async def full_catalog(*_args, **_kwargs):
        return 200, upstream_value

    monkeypatch.setattr(public, "call_bounded", full_catalog)
    with TestClient(app) as client:
        response = client.get("/api/assistants")
    assert response.status_code == 200
    assert len(response.content) <= ADMIN_CATALOG_BYTE_LIMIT
    assert name in response.text
