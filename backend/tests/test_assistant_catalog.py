"""Public Store projection of Developers-owned Assistant metadata."""

import asyncio
import copy
import hashlib
import threading

import pytest
from app import catalog
from app.concurrency import ExecutorSaturatedError
from app.main import app
from app.routers import public
from fastapi.testclient import TestClient

DIGEST = "sha256:" + ("a" * 64)
ICON_DIGEST = "sha256:" + ("b" * 64)
HELP_URL = "https://dashboard.example.com/api-keys"


def _assistant(**changes) -> dict[str, object]:
    """One entry in the exact shape Developers publishes (developers-api resolve.rs catalog value)."""
    value = {
        "assistant_id": "hello-world",
        "name": "Hello World",
        "summary": "Greets the Team.",
        "description": "Greets the Team and keeps the greeting short.",
        "links": {"site": "https://hello.example.org/", "github": "https://github.com/TheShimpz"},
        "assistant_version": "10.0.0",
        "creators": ["@shimpz"],
        "github": "https://github.com/TheShimpz/hello-world",
        "source_digest": DIGEST,
        "icon_digest": ICON_DIGEST,
        "platforms": ["linux/amd64", "linux/arm64"],
        "allowed_hosts": ["api.example.com"],
        "integrations": [{"id": "github", "provider": "github", "scopes": ["repo:read"]}],
        "stored_inputs": [
            {
                "id": "api-token",
                "kind": "password",
                "label": "API token",
                "description": "Create an API token in the example dashboard and copy it.",
                "help_url": HELP_URL,
            }
        ],
        "actions": [
            {
                "id": "hello",
                "integrations": ["github"],
                "stored_inputs": ["api-token"],
                "human_requests": ["approval", "input:text"],
                "effect": "read_only",
                "description": "Say hello.",
            }
        ],
    }
    value.update(changes)
    return value


def _catalog(*assistants: dict[str, object], locale: str = "en") -> dict[str, object]:
    """The exact envelope Developers serves for one requested locale."""
    return {"version": 1, "locale": locale, "assistants": list(assistants)}


def test_projects_only_bounded_browser_metadata() -> None:
    projected = catalog.project_catalog(_catalog(_assistant()), "en")

    assert projected == {
        "version": 1,
        "locale": "en",
        "assistants": [
            {
                "assistant_id": "hello-world",
                "name": "Hello World",
                "summary": "Greets the Team.",
                "description": "Greets the Team and keeps the greeting short.",
                "links": {"site": "https://hello.example.org/", "github": "https://github.com/TheShimpz"},
                "assistant_version": "10.0.0",
                "creators": ["@shimpz"],
                "github": "https://github.com/TheShimpz/hello-world",
                "source_digest": DIGEST,
                "icon_digest": ICON_DIGEST,
                "platforms": ["linux/amd64", "linux/arm64"],
                "allowed_hosts": ["api.example.com"],
                "integrations": [{"id": "github", "provider": "github", "scopes": ["repo:read"]}],
                "stored_inputs": [
                    {
                        "id": "api-token",
                        "label": "API token",
                        "description": "Create an API token in the example dashboard and copy it.",
                        "help_url": HELP_URL,
                    }
                ],
                "actions": [
                    {
                        "id": "hello",
                        "integrations": ["github"],
                        "human_requests": ["approval", "input:text"],
                        "effect": "read_only",
                        "description": "Say hello.",
                    }
                ],
            }
        ],
    }
    serialized = str(projected)
    assert "image_reference" not in serialized
    # A Stored Input projects only its identifier and localized label; its canonical description stays upstream.
    assert "Used to call the API." not in serialized


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(extra=True),
        lambda value: value.pop("locale"),
        lambda value: value.update(locale="pt"),
        lambda value: value.update(locale=None),
        lambda value: value.update(version=2),
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
        lambda value: value["assistants"][0]["stored_inputs"][0].pop("help_url"),
        lambda value: value["assistants"][0]["stored_inputs"][0].update(help_url="http://example.com/keys"),
        lambda value: value["assistants"][0]["stored_inputs"][0].update(help_url="https://example.com/keys#new"),
        lambda value: value["assistants"][0]["stored_inputs"][0].update(description="Line one.\nLine two."),
        lambda value: value["assistants"][0]["stored_inputs"].append(dict(value["assistants"][0]["stored_inputs"][0])),
        lambda value: value["assistants"][0].update(
            stored_inputs=[
                {"id": f"key-{index}", "kind": "password", "label": "Key", "description": "Key.", "help_url": HELP_URL}
                for index in range(9)
            ]
        ),
        lambda value: value["assistants"][0]["actions"][0].update(stored_inputs=["undeclared"]),
        lambda value: value["assistants"][0]["actions"][0].update(stored_inputs=["api-token", "api-token"]),
        lambda value: value["assistants"][0].pop("description"),
        lambda value: value["assistants"][0].update(description=""),
        lambda value: value["assistants"][0].update(description=" Leading space."),
        lambda value: value["assistants"][0].update(description="Line\nbreak."),
        lambda value: value["assistants"][0].update(description="C1\u0085control."),
        lambda value: value["assistants"][0].update(description="Bidi\u202eoverride."),
        lambda value: value["assistants"][0].update(description="Line\u2028separator."),
        lambda value: value["assistants"][0].update(description="Decomposed e\u0301."),
        lambda value: value["assistants"][0].update(description="d" * 501),
        lambda value: value["assistants"][0].update(description=None),
        lambda value: value["assistants"][0].pop("links"),
        lambda value: value["assistants"][0].update(links=None),
        lambda value: value["assistants"][0].update(links=["https://hello.example.org/"]),
        lambda value: value["assistants"][0]["links"].update(mastodon="https://mastodon.social/@shimpz"),
        lambda value: value["assistants"][0]["links"].update(github="https://gitlab.com/TheShimpz"),
        lambda value: value["assistants"][0]["links"].update(github="https://github.com.evil.example/TheShimpz"),
        lambda value: value["assistants"][0]["links"].update(x="https://twitter.com/shimpz"),
        lambda value: value["assistants"][0]["links"].update(x="https://www.x.com/shimpz"),
        lambda value: value["assistants"][0]["links"].update(youtube="https://m.youtube.com/@shimpz"),
        lambda value: value["assistants"][0]["links"].update(linkedin="https://uk.linkedin.com/in/shimpz"),
        lambda value: value["assistants"][0]["links"].update(instagram="https://instagr.am/shimpz"),
        lambda value: value["assistants"][0]["links"].update(site="http://hello.example.org/"),
        lambda value: value["assistants"][0]["links"].update(site="https://hello.example.org"),
        lambda value: value["assistants"][0]["links"].update(site="https://127.0.0.1/"),
        lambda value: value["assistants"][0]["links"].update(site="https://intranet.local/"),
        lambda value: value["assistants"][0]["links"].update(site="https://xn--80ak6aa92e.com/"),
        lambda value: value["assistants"][0]["links"].update(site="https://hello.example.org:8443/"),
        lambda value: value["assistants"][0]["links"].update(site="https://user@hello.example.org/"),
        lambda value: value["assistants"][0]["links"].update(site="https://hello.example.org/#top"),
        lambda value: value["assistants"][0]["links"].update(site="https://hello.example.org/a/../b"),
        lambda value: value["assistants"][0]["links"].update(site="https://Hello.example.org/"),
        lambda value: value["assistants"][0]["links"].update(site="https://hello.example.org/" + "a" * 231),
        lambda value: value["assistants"][0]["links"].update(site=42),
        lambda value: value["assistants"][0]["actions"][0].pop("effect"),
        lambda value: value["assistants"][0]["actions"][0].update(effect="destructive"),
        lambda value: value["assistants"][0]["actions"][0].update(effect=["read_only"]),
        lambda value: value["assistants"][0]["actions"][0].pop("description"),
        lambda value: value["assistants"][0]["actions"][0].update(description=""),
        lambda value: value["assistants"][0]["actions"][0].update(description="a" * 121),
        lambda value: value["assistants"][0]["actions"][0].update(description="Say hello. "),
        lambda value: value["assistants"][0]["stored_inputs"][0].update(label="l" * 121),
        lambda value: value["assistants"][0]["stored_inputs"][0].update(label=""),
        lambda value: value["assistants"][0]["stored_inputs"][0].update(description="d" * 501),
    ],
)
def test_rejects_ambiguous_or_executable_catalog_data(mutate) -> None:
    value = _catalog(_assistant())
    mutate(value)

    with pytest.raises(catalog.CatalogError):
        catalog.project_catalog(value, "en")


def test_admits_every_link_kind_on_its_host_in_canonical_order() -> None:
    links = {
        "instagram": "https://www.instagram.com/shimpz",
        "linkedin": "https://www.linkedin.com/company/shimpz",
        "youtube": "https://www.youtube.com/@shimpz",
        "x": "https://x.com/shimpz",
        "github": "https://github.com/TheShimpz",
        "site": "https://hello.example.org/docs?tab=about",
    }
    projected = catalog.project_catalog(_catalog(_assistant(links=links)), "en")["assistants"][0]["links"]
    assert list(projected) == ["site", "github", "x", "youtube", "linkedin", "instagram"]
    assert projected == links
    bare = {
        "youtube": "https://youtube.com/@shimpz",
        "linkedin": "https://linkedin.com/in/shimpz",
        "instagram": "https://instagram.com/shimpz",
        "site": "https://hello.example.org/" + "a" * 230,
    }
    assert catalog.project_catalog(_catalog(_assistant(links=bare)), "en")["assistants"][0]["links"] == {
        kind: bare[kind] for kind in ("site", "youtube", "linkedin", "instagram")
    }
    assert catalog.project_catalog(_catalog(_assistant(links={})), "en")["assistants"][0]["links"] == {}


def test_admits_localized_display_copy_up_to_its_catalog_bounds() -> None:
    assistant = _assistant(
        description="D" * 499 + "\u00e9",
        stored_inputs=[
            {
                "id": "api-token",
                "kind": "password",
                "label": "\u00e7" * 120,
                "description": "d" * 500,
                "help_url": HELP_URL,
            }
        ],
    )
    assistant["actions"][0].update(effect="mutating", description="\u00e1" * 120)
    projected = catalog.project_catalog(_catalog(assistant, locale="pt"), "pt")["assistants"][0]
    assert projected["description"] == "D" * 499 + "\u00e9"
    assert projected["actions"][0]["effect"] == "mutating"
    assert projected["actions"][0]["description"] == "\u00e1" * 120
    assert projected["stored_inputs"] == [
        {"id": "api-token", "label": "\u00e7" * 120, "description": "d" * 500, "help_url": HELP_URL}
    ]


@pytest.mark.parametrize("locale", ["ar", "de", "en", "es", "fr", "ja", "pt", "zh"])
def test_projects_exactly_the_requested_locale(locale) -> None:
    projected = catalog.project_catalog(_catalog(_assistant(summary=f"Summary ({locale})."), locale=locale), locale)
    assert projected["locale"] == locale
    assert projected["assistants"][0]["summary"] == f"Summary ({locale})."


@pytest.mark.parametrize("requested", ["it", "EN", "", None])
def test_refuses_a_locale_outside_the_closed_set(requested) -> None:
    with pytest.raises(catalog.CatalogError):
        catalog.project_catalog(_catalog(_assistant(), locale=requested), requested)


def _with_actions(count: int) -> dict[str, object]:
    action = _assistant()["actions"][0]
    return _assistant(actions=[{**action, "id": f"action-{index}"} for index in range(count)])


def test_an_assistant_with_the_producer_maximum_of_actions_is_projected() -> None:
    projected = catalog.project_catalog(_catalog(_with_actions(128)), "en")
    assert len(projected["assistants"][0]["actions"]) == 128
    with pytest.raises(catalog.CatalogError):
        catalog.project_catalog(_catalog(_with_actions(129)), "en")


def test_public_route_caches_only_a_valid_developers_catalog_per_locale(monkeypatch) -> None:
    requested: list[str] = []

    def valid_catalog(*args, **_kwargs):
        path = args[2]
        requested.append(path)
        locale = path.rpartition("=")[2]
        return 200, _catalog(_assistant(summary=f"Summary ({locale})."), locale=locale)

    monkeypatch.setattr(public, "call", valid_catalog)
    with TestClient(app) as client:
        english = client.get("/api/assistants?locale=en")
        portuguese = client.get("/api/assistants?locale=pt")

    assert requested == ["/api/v1/assistants?locale=en", "/api/v1/assistants?locale=pt"]
    for response, locale in ((english, "en"), (portuguese, "pt")):
        assert response.status_code == 200
        assert response.headers["cache-control"] == "public, max-age=60, s-maxage=300"
        assert response.json()["locale"] == locale
        assert response.json()["assistants"][0]["summary"] == f"Summary ({locale})."
        assert response.json()["assistants"][0]["source_digest"] == DIGEST


@pytest.fixture(autouse=True)
def _fresh_catalogs():
    """Each test starts with no locale's catalog and no icon kept."""
    public._catalogs.clear()
    public._icons.clear()
    yield
    public._catalogs.clear()
    public._icons.clear()


def test_a_burst_of_visitors_shares_one_read_and_the_next_minute_reuses_it(monkeypatch) -> None:
    calls = []
    release = threading.Event()

    def slow_catalog(*args, **_kwargs):
        calls.append(args[2])
        release.wait(5)
        return 200, _catalog(_assistant(), locale="en")

    monkeypatch.setattr(public, "call", slow_catalog)

    async def burst():
        visitors = [asyncio.create_task(public._served_catalog("en")) for _ in range(8)]
        await asyncio.sleep(0.05)
        release.set()
        return await asyncio.gather(*visitors)

    served = asyncio.run(burst())
    assert len(set(served)) == 1 and served[0] is not None
    assert calls == ["/api/v1/assistants?locale=en"]
    # Within the minute the kept catalog answers without Developers; past it, the catalog is read again.
    assert asyncio.run(public._served_catalog("en")) == served[0]
    assert len(calls) == 1
    kept_at, body = public._catalogs["en"]
    public._catalogs["en"] = (kept_at - public.CATALOG_CACHE_SECONDS, body)
    assert asyncio.run(public._served_catalog("en"))[1] == body
    assert len(calls) == 2


def test_a_kept_catalog_tells_later_caches_how_old_it_is(monkeypatch) -> None:
    monkeypatch.setattr(public, "call", lambda *_args, **_kwargs: (200, _catalog(_assistant(), locale="en")))
    with TestClient(app) as client:
        assert client.get("/api/assistants?locale=en").headers["age"] == "0"
        read_at, body = public._catalogs["en"]
        public._catalogs["en"] = (read_at - 59, body)
        assert client.get("/api/assistants?locale=en").headers["age"] == "59"


def test_reads_of_different_locales_never_exceed_what_developers_loads_at_once(monkeypatch) -> None:
    active, peak = [], []
    lock = threading.Lock()

    def counted(*args, **_kwargs):
        with lock:
            active.append(args[2])
            peak.append(len(active))
        threading.Event().wait(0.05)
        with lock:
            active.remove(args[2])
        return 200, _catalog(_assistant(), locale=args[2].rpartition("=")[2])

    monkeypatch.setattr(public, "call", counted)

    async def cold_locales():
        return await asyncio.gather(*(public._served_catalog(locale) for locale in ("en", "pt", "es", "fr", "de")))

    assert all(body is not None for body in asyncio.run(cold_locales()))
    assert max(peak) <= public.DEVELOPERS_CATALOG_LOADS


def test_a_read_that_waits_past_its_deadline_for_a_load_slot_is_refused(monkeypatch) -> None:
    monkeypatch.setattr(public, "VERIFY_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(public, "call", lambda *_args, **_kwargs: (200, _catalog(_assistant(), locale="en")))
    monkeypatch.setattr(public, "call_asset", lambda *_args, **_kwargs: (200, b"icon"))

    async def starved():
        release = asyncio.Event()

        async def hold(kind, size):
            async with public._developers_slot(kind, size) as admitted:
                assert admitted
                await release.wait()

        holders = [
            asyncio.create_task(hold(kind, size))
            for kind, size in (("catalog", public.DEVELOPERS_CATALOG_LOADS), ("icon", public.DEVELOPERS_ICON_LOADS))
            for _ in range(size)
        ]
        await asyncio.sleep(0)
        refused = (
            await public._served_catalog("en"),
            await public._read_icon(("a" * 64, hashlib.sha256(b"icon").hexdigest())),
        )
        release.set()
        await asyncio.gather(*holders)
        return refused

    assert asyncio.run(starved()) == (None, None)


def test_a_failed_catalog_read_is_never_kept(monkeypatch) -> None:
    answers = iter([(503, {}), (200, _catalog(_assistant(), locale="en"))])
    monkeypatch.setattr(public, "call", lambda *_args, **_kwargs: next(answers))
    assert asyncio.run(public._served_catalog("en")) is None
    assert "en" not in public._catalogs
    assert asyncio.run(public._served_catalog("en")) is not None


@pytest.mark.parametrize(
    "query",
    ["", "?locale=", "?locale=it", "?locale=EN", "?locale=pt&locale=en", "?locale=pt&page=2", "?page=2&locale=pt"],
)
def test_public_route_refuses_any_query_but_one_closed_locale(monkeypatch, query) -> None:
    def unexpected(*_args, **_kwargs):
        raise AssertionError("Developers must not be called for an invalid locale")

    monkeypatch.setattr(public, "call", unexpected)
    with TestClient(app) as client:
        response = client.get(f"/api/assistants{query}")

    assert response.status_code == 400
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {"detail": "Assistant catalog locale is invalid"}


def test_public_route_refuses_a_catalog_in_another_locale(monkeypatch) -> None:
    def mismatched(*_args, **_kwargs):
        return 200, _catalog(_assistant(), locale="en")

    monkeypatch.setattr(public, "call", mismatched)
    with TestClient(app) as client:
        response = client.get("/api/assistants?locale=pt")

    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"


def test_public_route_projects_and_serializes_the_catalog_off_the_event_loop(monkeypatch) -> None:
    workers: list[tuple[str, bool]] = []
    project = catalog.project_catalog

    def on_loop() -> bool:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return False
        return True

    def valid_catalog(*_args, **_kwargs):
        workers.append((threading.current_thread().name, on_loop()))
        return 200, _catalog(_assistant())

    def projected(value, locale):
        workers.append((threading.current_thread().name, on_loop()))
        return project(value, locale)

    monkeypatch.setattr(public, "call", valid_catalog)
    monkeypatch.setattr(public.catalog, "project_catalog", projected)
    with TestClient(app) as client:
        response = client.get("/api/assistants?locale=en")

    assert response.status_code == 200
    assert len(workers) == 2
    assert all(name.startswith("shimpz-control") and not loop for name, loop in workers)


def test_public_route_refuses_the_catalog_when_control_admission_is_full(monkeypatch) -> None:
    def must_not_run(*_args, **_kwargs):
        raise AssertionError("a saturated control executor must not run the catalog")

    def saturated(*_args, **_kwargs):
        raise ExecutorSaturatedError("blocking worker admission is full")

    monkeypatch.setattr(public, "call", must_not_run)
    monkeypatch.setattr(public.CONTROL_EXECUTOR, "submit", saturated)
    with TestClient(app) as client:
        response = client.get("/api/assistants?locale=en")

    assert response.status_code == 429
    assert "assistants" not in response.text


def test_public_icon_route_verifies_and_immutably_caches_exact_bytes(monkeypatch) -> None:
    contents = b"canonical icon"
    icon_hash = hashlib.sha256(contents).hexdigest()

    reads = []

    def valid_icon(*args, **_kwargs):
        reads.append(args[1])
        return 200, contents

    monkeypatch.setattr(public, "call_asset", valid_icon)
    with TestClient(app) as client:
        response = client.get(f"/api/assistant-icons/{'a' * 64}/{icon_hash}.png")

    assert response.status_code == 200
    assert response.content == contents
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
    # A verified icon is kept: the next visitor gets it without another Developers read.
    with TestClient(app) as client:
        assert client.get(f"/api/assistant-icons/{'a' * 64}/{icon_hash}.png").content == contents
    assert reads == [f"/api/v1/assistant-publications/sha256:{'a' * 64}/icon.png"]


def test_public_icon_route_fails_closed_on_digest_mismatch(monkeypatch) -> None:
    monkeypatch.setattr(public, "call_asset", lambda *_args, **_kwargs: (200, b"wrong icon"))
    with TestClient(app) as client:
        response = client.get(f"/api/assistant-icons/{'a' * 64}/{'b' * 64}.png")

    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"


def test_public_icon_route_refuses_a_malformed_digest_before_developers(monkeypatch) -> None:
    def must_not_run(*_args, **_kwargs):
        raise AssertionError("a malformed icon digest must not reach Developers")

    monkeypatch.setattr(public, "call_asset", must_not_run)
    with TestClient(app) as client:
        response = client.get("/api/assistant-icons/not-a-hash/not-a-hash.png")

    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("upstream", [(502, {}), (200, {"version": 1, "locale": "en", "assistants": "bad"})])
def test_public_route_fails_closed_without_cache(monkeypatch, upstream) -> None:
    def invalid_catalog(*_args, **_kwargs):
        return upstream

    monkeypatch.setattr(public, "call", invalid_catalog)
    with TestClient(app) as client:
        response = client.get("/api/assistants?locale=en")

    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {"detail": "Assistant catalog is unavailable"}


# Admin's byte cap for the Store catalog response (admin/backend/chat/store_catalog.py).
ADMIN_CATALOG_BYTE_LIMIT = 4 * 1024 * 1024


def test_a_full_utf8_catalog_is_served_as_utf8_within_the_consumer_byte_limit(monkeypatch) -> None:
    """The response keeps multibyte text as UTF-8; escaping it would push a valid full catalog past Admin's cap."""
    name = "Á" * 80
    summary = "É" * 80

    def entry(index: int) -> dict[str, object]:
        # Long public texts make a full catalog near the consumer cap, as real publications can be.
        return _assistant(
            assistant_id=f"assistant-{index:04d}",
            name=name,
            summary=summary,
            allowed_hosts=[f"{'á' * 60}{host:02d}.example.com" for host in range(16)],
        )

    upstream_value = _catalog(*(entry(index) for index in range(1000)))

    def full_catalog(*_args, **_kwargs):
        return 200, upstream_value

    monkeypatch.setattr(public, "call", full_catalog)
    with TestClient(app) as client:
        response = client.get("/api/assistants?locale=en")
    assert response.status_code == 200
    assert len(response.content) <= ADMIN_CATALOG_BYTE_LIMIT
    assert name in response.text


def test_the_summary_is_a_short_description_of_at_most_eighty_characters(monkeypatch) -> None:
    for summary in ("s" * 80, "s" * 79 + "\U0001f44b"):
        catalog_value = _catalog(_assistant(summary=summary))
        monkeypatch.setattr(public, "call", lambda *_args, value=catalog_value, **_kwargs: (200, value))
        public._catalogs.clear()
        with TestClient(app) as client:
            response = client.get("/api/assistants?locale=en")
        assert response.status_code == 200
        assert response.json()["assistants"][0]["summary"] == summary
    over = _catalog(_assistant(summary="s" * 81))
    monkeypatch.setattr(public, "call", lambda *_args, **_kwargs: (200, over))
    public._catalogs.clear()
    with TestClient(app) as client:
        assert client.get("/api/assistants?locale=en").status_code != 200


def test_an_action_may_use_several_declared_stored_inputs() -> None:
    keys = [
        {"id": f"key-{index}", "kind": "password", "label": "Key", "description": "Key.", "help_url": HELP_URL}
        for index in range(8)
    ]
    names = [key["id"] for key in keys]
    assistant = _assistant(stored_inputs=keys)
    assistant["actions"][0]["stored_inputs"] = names
    projected = catalog.project_catalog(_catalog(assistant), "en")
    assert projected["assistants"][0]["actions"][0]["id"] == "hello"
    assistant["actions"][0]["stored_inputs"] = [*names, "key-8"]
    with pytest.raises(catalog.CatalogError):
        catalog.project_catalog(_catalog(assistant), "en")


def test_icons_are_read_two_at_a_time_and_kept_within_their_budget(monkeypatch) -> None:
    active, peak = [], []
    lock = threading.Lock()

    def counted(*args, **_kwargs):
        with lock:
            active.append(args[1])
            peak.append(len(active))
        threading.Event().wait(0.02)
        with lock:
            active.remove(args[1])
        return 200, args[1].encode()

    monkeypatch.setattr(public, "call_asset", counted)
    sources = [f"{index:064x}" for index in range(12)]

    def icon(source: str) -> str:
        return hashlib.sha256(f"/api/v1/assistant-publications/sha256:{source}/icon.png".encode()).hexdigest()

    async def grid():
        return await asyncio.gather(*(public.assistant_icon(source, icon(source)) for source in sources))

    assert all(response.status_code == 200 for response in asyncio.run(grid()))
    assert max(peak) <= public.DEVELOPERS_ICON_LOADS
    monkeypatch.setattr(public, "MAX_KEPT_ICONS", 3)
    public._keep_icon(("x", "y"), b"z")
    assert len(public._icons) == 3 and ("x", "y") in public._icons
    monkeypatch.setattr(public, "MAX_KEPT_ICON_BYTES", 1)
    public._keep_icon(("big", "icon"), b"zz")
    assert public._icons == {}


def test_visitors_asking_for_one_cold_icon_together_share_one_read(monkeypatch) -> None:
    contents = b"one icon"
    reads = []
    release = threading.Event()

    def slow_icon(*args, **_kwargs):
        reads.append(args[1])
        release.wait(5)
        return 200, contents

    monkeypatch.setattr(public, "call_asset", slow_icon)
    icon_hash = hashlib.sha256(contents).hexdigest()

    async def burst():
        visitors = [asyncio.create_task(public.assistant_icon("a" * 64, icon_hash)) for _ in range(24)]
        await asyncio.sleep(0.05)
        release.set()
        return await asyncio.gather(*visitors)

    assert all(response.status_code == 200 for response in asyncio.run(burst()))
    assert len(reads) == 1
    assert public._icon_reads == {}


def test_a_grid_of_cold_icons_waits_on_the_loop_and_leaves_the_catalog_its_executor(monkeypatch) -> None:
    def icon(*args, **_kwargs):
        threading.Event().wait(0.01)
        return 200, args[1].encode()

    monkeypatch.setattr(public, "call_asset", icon)
    monkeypatch.setattr(public, "call", lambda *_args, **_kwargs: (200, _catalog(_assistant(), locale="en")))
    sources = [f"{index:064x}" for index in range(24)]

    def digest(source: str) -> str:
        return hashlib.sha256(f"/api/v1/assistant-publications/sha256:{source}/icon.png".encode()).hexdigest()

    async def page():
        icons = [public.assistant_icon(source, digest(source)) for source in sources]
        return await asyncio.gather(public._served_catalog("en"), *icons)

    catalog_read, *icons = asyncio.run(page())
    assert catalog_read is not None
    assert all(response.status_code == 200 for response in icons)


def test_icons_past_the_pending_bound_are_refused_and_never_queued(monkeypatch) -> None:
    monkeypatch.setattr(public, "MAX_PENDING_ICON_READS", 1)
    release = threading.Event()

    def slow(*_args, **_kwargs):
        release.wait(5)
        return 200, b"icon"

    monkeypatch.setattr(public, "call_asset", slow)
    digest = hashlib.sha256(b"icon").hexdigest()

    async def burst():
        first = asyncio.create_task(public.assistant_icon("a" * 64, digest))
        joined = asyncio.create_task(public.assistant_icon("a" * 64, digest))
        await asyncio.sleep(0.02)
        other = await public.assistant_icon("b" * 64, digest)
        release.set()
        return other, await first, await joined

    other, first, joined = asyncio.run(burst())
    assert other.status_code == 503
    assert (first.status_code, joined.status_code) == (200, 200)
