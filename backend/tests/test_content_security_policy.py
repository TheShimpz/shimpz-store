import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main as store
from app import middleware
from app.routers import static

FIRST = "'sha256-E2N7hQ3NwGfqO4gTMTO7EKdeuUdNjqWRsO93pk0dKzQ='"
SECOND = "'sha256-JY9Zlt5CTKKcht1Ime1WdiZbsBz8Z7rPGggLHARyZHw='"
TRUSTED_TYPES = "require-trusted-types-for 'script'; trusted-types svelte-trusted-html"


def _page(scripts: str) -> str:
    return _exact_page(f"{scripts}; {TRUSTED_TYPES}")


def _exact_page(policy: str) -> str:
    return (
        '<!doctype html><head><meta charset="utf-8" />\n'
        f'<meta http-equiv="content-security-policy" content="{policy}">\n'
        "</head><body><script>start()</script></body>"
    )


def _build(root: Path) -> Path:
    pages = {
        "en.html": _page(f"script-src 'self' {SECOND}"),
        "pt.html": _page(f"script-src 'self' {FIRST} {SECOND}"),
        "en/assistants.html": _page(f"script-src 'self' {FIRST}"),
        "en/404.html": _page("script-src 'self'"),
        "brand/notes.txt": "not a page",
    }
    for relative, content in pages.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return root


def _script_sources(policy: str) -> list[str]:
    return re.search(r"(?:^|; )script-src ([^;]*)", policy).group(1).split()


def test_the_build_inline_scripts_are_admitted_by_their_exact_hashes(tmp_path):
    """The header admits the union of the hashes each page's own build policy names, a page may name none."""
    assert middleware.build_script_sources(_build(tmp_path)) == (FIRST.encode(), SECOND.encode())


@pytest.mark.parametrize(
    "document",
    [
        "<!doctype html><script>start()</script>",
        _page(f"script-src 'self' 'unsafe-inline' {FIRST}"),
        _page(f"script-src 'self' {FIRST} https://cdn.example"),
        _page(f"default-src 'self' {FIRST}"),
        _page(f"script-src {FIRST}"),
        _page("script-src 'self' 'sha256-short='"),
        _page(f"script-src  'self' {FIRST}"),
        _exact_page(f"script-src 'self' {FIRST}"),
        _exact_page(f"script-src 'self' {FIRST}; require-trusted-types-for 'script'"),
        _exact_page(f"script-src 'self' {FIRST}; {TRUSTED_TYPES} default"),
        _exact_page(f"script-src 'self' {FIRST} {TRUSTED_TYPES}"),
        _page(f"script-src 'self' {FIRST}") + _page(f"script-src 'self' {FIRST}"),
        '<meta http-equiv="content-security-policy" content="script-src',
    ],
)
def test_a_page_without_one_exact_build_policy_refuses_the_whole_build(tmp_path, document):
    _build(tmp_path)
    (tmp_path / "en" / "about.html").write_text(document, encoding="utf-8")

    with pytest.raises(middleware.BuildPolicyError):
        middleware.build_script_sources(tmp_path)


def test_no_response_admits_unsafe_inline_scripts(monkeypatch, tmp_path):
    build = _build(tmp_path)
    monkeypatch.setattr(static, "BUILD", build)
    monkeypatch.setattr(middleware, "_PAGE_HEADERS", middleware.page_headers(build))
    expected = ["'self'", FIRST, SECOND]

    with TestClient(store.app) as client:
        responses = [
            client.get("/api/health"),
            client.get("/", follow_redirects=False),
            client.get("/en"),
            client.get("/en/assistants"),
            client.get("/en/missing", headers={"accept": "text/html"}),
            client.get("/_app/missing.js"),
        ]

    for response in responses:
        policy = response.headers["content-security-policy"]
        assert len(response.headers.get_list("content-security-policy")) == 1
        assert _script_sources(policy) == expected, response.url
        assert "'unsafe-inline'" not in _script_sources(policy)
        assert "'unsafe-eval'" not in _script_sources(policy)


def test_every_response_refuses_plain_strings_at_dom_injection_sinks(monkeypatch, tmp_path):
    build = _build(tmp_path)
    monkeypatch.setattr(static, "BUILD", build)
    monkeypatch.setattr(middleware, "_PAGE_HEADERS", middleware.page_headers(build))

    with TestClient(store.app) as client:
        responses = [client.get("/api/health"), client.get("/en"), client.get("/_app/missing.js")]

    for response in responses:
        directives = response.headers["content-security-policy"].split("; ")
        assert "require-trusted-types-for 'script'" in directives, response.url
        # Svelte's template policy is the only one a page may create; no permissive default policy exists.
        assert "trusted-types svelte-trusted-html" in directives, response.url


def test_without_a_build_only_this_origin_may_run_scripts(tmp_path):
    policy = dict(middleware.page_headers(tmp_path / "absent"))[b"content-security-policy"].decode()

    assert _script_sources(policy) == ["'self'"]


def test_pages_load_images_and_open_connections_only_from_this_origin(tmp_path):
    policy = dict(middleware.page_headers(tmp_path / "absent"))[b"content-security-policy"].decode()
    directives = dict(directive.split(" ", 1) for directive in policy.split("; ") if " " in directive)

    assert directives["img-src"] == "'self'"
    assert directives["connect-src"] == "'self'"
