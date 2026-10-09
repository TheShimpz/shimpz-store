import base64
import hashlib
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app import main as store
from app import middleware
from app.routers import static

BOOTSTRAP = '\n\t{ __sveltekit_x = { base: "" }; Promise.all([import("./_app/start.js")]); }\n'
REDIRECT = 'location.href="/en";'


def _source(script: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(script.encode()).digest()).decode() + "'"


def _build(root: Path) -> Path:
    pages = {
        "index.html": f"<!doctype html><script>{REDIRECT}</script>",
        "en.html": f'<head><script src="/_app/x.js"></script></head><body><script>{BOOTSTRAP}</script></body>',
        "pt.html": f"<body><script>{BOOTSTRAP}</script></body>",
        "en/assistants/embed.html": f'<script type="application/json">{{"a":1}}</script><script>{BOOTSTRAP}</script>',
        "en/404.html": "<p>missing</p>",
    }
    for relative, content in pages.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return root


def _script_sources(policy: str) -> list[str]:
    return re.search(r"(?:^|; )script-src ([^;]*)", policy).group(1).split()


def test_the_build_inline_scripts_are_admitted_by_their_exact_hashes(tmp_path):
    expected = sorted({_source(REDIRECT), _source(BOOTSTRAP), _source('{"a":1}')})

    assert [source.decode() for source in middleware.build_script_sources(_build(tmp_path))] == expected


def test_no_response_admits_unsafe_inline_scripts(monkeypatch, tmp_path):
    build = _build(tmp_path)
    monkeypatch.setattr(static, "BUILD", build)
    monkeypatch.setattr(middleware, "BUILD", build)
    expected = ["'self'", *sorted({_source(REDIRECT), _source(BOOTSTRAP), _source('{"a":1}')})]

    with TestClient(store.app) as client:
        responses = [
            client.get("/api/health"),
            client.get("/"),
            client.get("/en"),
            client.get("/en/assistants/embed"),
            client.get("/en/missing", headers={"accept": "text/html"}),
            client.get("/_app/missing.js"),
        ]

    for response in responses:
        policy = response.headers["content-security-policy"]
        assert len(response.headers.get_list("content-security-policy")) == 1
        assert _script_sources(policy) == expected, response.url
        assert "'unsafe-inline'" not in _script_sources(policy)
        assert "'unsafe-eval'" not in _script_sources(policy)


def test_without_a_build_only_this_origin_may_run_scripts(tmp_path):
    page, embed = middleware.security_headers(tmp_path / "absent")

    for headers in (page, embed):
        policy = dict(headers)[b"content-security-policy"].decode()
        assert _script_sources(policy) == ["'self'"]
