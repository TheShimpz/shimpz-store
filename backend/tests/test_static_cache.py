import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main as store
from app.routers import static


def _write(root: Path, relative: str, content: str) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def test_html_navigation_always_revalidates(monkeypatch, tmp_path):
    _write(tmp_path, "en.html", "home")
    _write(tmp_path, "en/assistants.html", "store")
    _write(tmp_path, "_app/immutable/chunks/never-cache.html", "html")
    monkeypatch.setattr(static, "BUILD", tmp_path)

    with TestClient(store.app) as client:
        for url in (
            "/en",
            "/en/assistants?assistant=hello-pulse",
            "/_app/immutable/chunks/never-cache.html",
        ):
            response = client.get(url)
            assert response.status_code == 200
            assert response.headers["cache-control"] == "public, no-cache, max-age=0, must-revalidate, no-transform"
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


def test_missing_not_found_document_and_foreign_path_fail_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(static, "BUILD", tmp_path)

    assert not static.is_not_found_document(tmp_path.parent / "404.html")
    with TestClient(store.app) as client:
        response = client.get("/en/missing", headers={"Accept": "text/html"})

    assert response.status_code == 404
    assert response.text == "not found"


def test_files_resolving_outside_the_build_are_refused_while_a_linked_build_serves(monkeypatch, tmp_path):
    build = tmp_path / "build"
    _write(build, "en.html", "home")
    _write(tmp_path, "secret.txt", "secret sentinel")
    (build / "leak.txt").symlink_to(tmp_path / "secret.txt")
    (tmp_path / "linked-build").symlink_to(build)
    monkeypatch.setattr(static, "BUILD", tmp_path / "linked-build")

    assert static.resolve("leak.txt") is None
    assert static.resolve("../secret.txt") is None
    with TestClient(store.app) as client:
        leaked = client.get("/leak.txt", headers={"Accept": "text/html"})
        home = client.get("/en")

    assert leaked.status_code == 404
    assert "secret sentinel" not in leaked.text
    assert home.status_code == 200
    assert home.text == "home"


def test_a_path_holding_a_control_byte_names_no_file(monkeypatch, tmp_path):
    _write(tmp_path, "en/404.html", "english-not-found")
    _write(tmp_path, "index.html", "home")
    monkeypatch.setattr(static, "BUILD", tmp_path)

    assert static.resolve("index\x00.html") is None
    assert static.resolve("\x1f") is None
    with TestClient(store.app) as client:
        plain = [client.get(path) for path in ("/%00", "/index.html%00", "/%1f/x", "/en%0a")]
        navigation = client.get("/%00/x", headers={"Accept": "text/html"})

    assert all(response.status_code == 404 and response.text == "not found" for response in plain)
    assert navigation.status_code == 404
    assert navigation.text == "english-not-found"


def test_the_site_root_sends_every_visitor_to_the_english_home(monkeypatch, tmp_path):
    _write(tmp_path, "en.html", "english-home")
    monkeypatch.setattr(static, "BUILD", tmp_path)

    with TestClient(store.app) as client:
        redirects = [client.request(method, "/", follow_redirects=False) for method in ("GET", "HEAD")]
        landed = client.get("/")
        refused = client.post("/")

    for response in redirects:
        assert response.status_code == 308
        assert response.headers["location"] == "/en"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["x-request-id"]
    assert landed.text == "english-home"
    assert refused.status_code == 405
    assert refused.headers["allow"] == "GET"


def test_a_range_request_receives_the_whole_file_without_advertising_ranges(monkeypatch, tmp_path):
    _write(tmp_path, "_app/immutable/chunk.js", "0123456789")
    monkeypatch.setattr(static, "BUILD", tmp_path)

    with TestClient(store.app) as client:
        responses = [
            client.get("/_app/immutable/chunk.js", headers={"Range": "bytes=0-1"}),
            client.get("/_app/immutable/chunk.js", headers={"Range": "bytes=0-1,4-5"}),
            client.get("/_app/immutable/chunk.js", headers={"Range": "bytes=99-"}),
            client.get("/_app/immutable/chunk.js", headers={"Range": "bytes=+5", "If-Range": '"x"'}),
        ]

    for response in responses:
        assert response.status_code == 200
        assert response.content == b"0123456789"
        assert response.headers["content-length"] == "10"
        assert "accept-ranges" not in response.headers
        assert "content-range" not in response.headers


@pytest.mark.parametrize(
    ("name", "content_type"),
    [
        ("page.html", "text/html; charset=utf-8"),
        ("style.css", "text/css; charset=utf-8"),
        ("start.js", "text/javascript; charset=utf-8"),
        ("UPPER.JS", "text/javascript; charset=utf-8"),
        ("version.json", "application/json"),
        ("icon.png", "image/png"),
        ("mark.svg", "image/svg+xml"),
        ("robots.txt", "text/plain; charset=utf-8"),
        ("sitemap.xml", "text/xml; charset=utf-8"),
        ("font.woff", "font/woff"),
        ("font.woff2", "font/woff2"),
        ("favicon.ico", "image/vnd.microsoft.icon"),
        ("app.webmanifest", "application/manifest+json"),
        ("chunk.js.map", "application/octet-stream"),
        ("archive.js.gz", "application/octet-stream"),
        ("legacy.htm", "application/octet-stream"),
        ("trailing.", "application/octet-stream"),
        (".js", "application/octet-stream"),
    ],
)
def test_every_file_is_served_with_its_closed_media_type(monkeypatch, tmp_path, name, content_type):
    _write(tmp_path, f"files/{name}", "x")
    monkeypatch.setattr(static, "BUILD", tmp_path)

    with TestClient(store.app) as client:
        response = client.get(f"/files/{name}")

    assert response.status_code == 200
    assert response.headers["content-type"] == content_type


@pytest.mark.parametrize(
    ("mtime_ns", "size", "tag"),
    [
        (0, 0, '"0-0"'),
        (1, 1, '"1-1"'),
        (1_700_000_000_000_000_000, 4096, '"17979cfe362a0000-1000"'),
        (-1, 2**40, '"-1-10000000000"'),
        (-1_000_000_001, 3, '"-3b9aca01-3"'),
    ],
)
def test_the_entity_tag_names_the_integer_mtime_and_size(mtime_ns, size, tag):
    assert static.entity_tag(mtime_ns, size) == tag


@pytest.mark.parametrize(
    ("mtime_ns", "modified"),
    [
        (1_700_000_000_000_000_000, "Tue, 14 Nov 2023 22:13:20 GMT"),
        (1_700_000_000_999_999_000, "Tue, 14 Nov 2023 22:13:20 GMT"),
        (1_700_000_000_999_999_500, "Tue, 14 Nov 2023 22:13:20 GMT"),
        (1_700_000_000_999_999_999, "Tue, 14 Nov 2023 22:13:20 GMT"),
        (1_700_000_001_000_000_000, "Tue, 14 Nov 2023 22:13:21 GMT"),
        (0, "Thu, 01 Jan 1970 00:00:00 GMT"),
        (253_402_300_799_000_000_000, "Fri, 31 Dec 9999 23:59:59 GMT"),
        (253_402_300_799_999_999_999, "Fri, 31 Dec 9999 23:59:59 GMT"),
        (-1, None),
        (-1_000_000_000, None),
        (253_402_300_800_000_000_000, None),
    ],
)
def test_last_modified_floors_the_mtime_to_its_whole_second_within_four_digit_years(mtime_ns, modified):
    assert static.last_modified(mtime_ns) == modified


def test_a_served_file_carries_its_integer_validators(monkeypatch, tmp_path):
    _write(tmp_path, "en.html", "home")
    _write(tmp_path, "before-epoch.txt", "old")
    os.utime(tmp_path / "en.html", ns=(0, 1_700_000_000_999_999_999))
    os.utime(tmp_path / "before-epoch.txt", ns=(0, -1))
    monkeypatch.setattr(static, "BUILD", tmp_path)

    with TestClient(store.app) as client:
        page = client.get("/en")
        old = client.get("/before-epoch.txt")

    assert page.headers["etag"] == '"17979cfe71c4c9ff-4"'
    assert page.headers["last-modified"] == "Tue, 14 Nov 2023 22:13:20 GMT"
    assert old.headers["etag"] == '"-1-3"'
    assert "last-modified" not in old.headers
