from pathlib import Path

from fastapi.testclient import TestClient

from app import main as store
from app.routers import static


def _write(root: Path, relative: str, content: str) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def test_html_navigation_always_revalidates(monkeypatch, tmp_path):
    _write(tmp_path, "index.html", "home")
    _write(tmp_path, "en/assistants/embed.html", "embedded-store")
    _write(tmp_path, "_app/immutable/chunks/never-cache.html", "html")
    monkeypatch.setattr(static, "BUILD", tmp_path)

    with TestClient(store.app) as client:
        for url in (
            "/",
            "/en/assistants/embed?admin-frame=new-release",
            "/_app/immutable/chunks/never-cache.html",
        ):
            response = client.get(url)
            assert response.status_code == 200
            assert response.headers["cache-control"] == static.HTML_CACHE_CONTROL
            assert "immutable" not in response.headers["cache-control"]


def test_sveltekit_immutable_assets_keep_long_content_addressed_cache(monkeypatch, tmp_path):
    _write(tmp_path, "_app/immutable/chunks/AssistantStore.BfzPtRCS.js", "export default true")
    monkeypatch.setattr(static, "BUILD", tmp_path)

    with TestClient(store.app) as client:
        response = client.get("/_app/immutable/chunks/AssistantStore.BfzPtRCS.js?release=1")

    assert response.status_code == 200
    assert response.headers["cache-control"] == static.IMMUTABLE_CACHE_CONTROL
    assert response.text == "export default true"


def test_mutable_assets_and_missing_navigation_do_not_heuristically_cache(monkeypatch, tmp_path):
    _write(tmp_path, "brand/shimpz.svg", "<svg></svg>")
    _write(tmp_path, "_app/immutable-lookalike/chunk.js", "mutable")
    monkeypatch.setattr(static, "BUILD", tmp_path)

    with TestClient(store.app) as client:
        mutable = client.get("/brand/shimpz.svg")
        lookalike = client.get("/_app/immutable-lookalike/chunk.js")
        missing = client.get("/en/not-published-yet")

    assert mutable.status_code == 200
    assert mutable.headers["cache-control"] == static.HTML_CACHE_CONTROL
    assert lookalike.status_code == 200
    assert lookalike.headers["cache-control"] == static.HTML_CACHE_CONTROL
    assert missing.status_code == 404
    assert missing.headers["cache-control"] == static.HTML_CACHE_CONTROL


def test_html_misses_serve_localized_not_found_document(monkeypatch, tmp_path):
    _write(tmp_path, "en/404.html", "english-not-found")
    _write(tmp_path, "pt/404.html", "portuguese-not-found")
    monkeypatch.setattr(static, "BUILD", tmp_path)

    with TestClient(store.app) as client:
        localized = client.get("/pt/dead-route", headers={"Accept": "text/html"})
        unknown_locale = client.get("/xx/dead-route", headers={"Accept": "text/html"})
        no_locale = client.get("/dead-route", headers={"Accept": "text/html"})

    assert localized.status_code == 404
    assert localized.text == "portuguese-not-found"
    assert unknown_locale.status_code == 404
    assert unknown_locale.text == "english-not-found"
    assert no_locale.status_code == 404
    assert no_locale.text == "english-not-found"


def test_not_found_document_is_never_exposed_as_a_successful_page(monkeypatch, tmp_path):
    _write(tmp_path, "en/404.html", "english-not-found")
    monkeypatch.setattr(static, "BUILD", tmp_path)

    with TestClient(store.app) as client:
        responses = [
            client.get(path, headers={"Accept": "text/html"}) for path in ("/en/404", "/en/404/", "/en/404.html")
        ]

    assert all(response.status_code == 404 for response in responses)
    assert all(response.text == "english-not-found" for response in responses)


def test_non_html_miss_keeps_plain_text_response(monkeypatch, tmp_path):
    _write(tmp_path, "en/404.html", "english-not-found")
    monkeypatch.setattr(static, "BUILD", tmp_path)

    with TestClient(store.app) as client:
        response = client.get("/en/missing.js", headers={"Accept": "text/javascript,*/*"})

    assert response.status_code == 404
    assert response.text == "not found"
    assert response.headers["content-type"].startswith("text/plain")
