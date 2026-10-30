"""The Python Store's answer to each differential case, from the `app.*` functions themselves.

`prepare(work)` builds the shared environment once per process: a build tree (its spec is written beside it, so the
Rust side builds the same one), the two lease keys, and the Access credential files; it points the Python Store's
build at that tree before importing the modules that read it.
"""

import base64
import json
import os
import random
import sys
from pathlib import Path
from urllib.parse import parse_qsl

ROOT = Path(__file__).resolve().parent.parent
META = (
    '<meta http-equiv="content-security-policy" content="script-src \'self\'; '
    "require-trusted-types-for 'script'; trusted-types svelte-trusted-html\">"
)
CURRENT_KEY, PREVIOUS_KEY, ROTATED_KEY = b"n" * 32, b"q" * 32, b"r" * 32
# The build tree both sides serve: (relative path, contents) for files, (relative path, None, target) for links.
TREE = (
    ("build/en.html", META + "english-home"),
    ("build/pt.html", META + "portuguese-home"),
    ("build/en/404.html", META + "english-missing"),
    ("build/pt/404.html", META + "portuguese-missing"),
    ("build/fr/index.html", META + "french-index"),
    ("build/deep/x/404.html", META + "deep-missing"),
    ("build/index.html", META + "root-index"),
    ("build/_app/immutable/a.js", "asset-a"),
    ("build/_app/immutable/A.JS", "asset-upper"),
    ("build/_app/version.json", "{}"),
    ("build/robots.txt", "robots"),
    ("build/favicon.ico", "icon"),
    ("build/a b.html", META + "spaced"),
    ("build/é.html", META + "accented"),
    ("build/dir/inner.txt", "inner"),
    ("secret.txt", "outside"),
    ("build/inside-link", None, "robots.txt"),
    ("build/outside-link", None, "../secret.txt"),
)
_STATE: dict[str, object] = {}


def _install(path: Path, contents: bytes) -> Path:
    path.write_bytes(contents)
    path.chmod(0o400)
    return path


def prepare(work: Path) -> None:
    """Create the environment under `work` (once per process) and import the Python Store against it."""
    if _STATE:
        return
    for entry in TREE:
        target = work / entry[0]
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() and not target.is_symlink():
            if entry[1] is None:
                target.symlink_to(entry[2])
            else:
                target.write_text(entry[1], encoding="utf-8")
    keys = work / f"keys-{os.getpid()}"
    keys.mkdir(exist_ok=True)
    sys.path.insert(0, str(ROOT))
    import app.config

    app.config.BUILD = work / "build"
    from app import catalog, middleware, oauth_broker, ratelimit
    from app.protocol.http.v1 import strict_json
    from app.routers import static

    _STATE.update(
        catalog=catalog,
        middleware=middleware,
        oauth_broker=oauth_broker,
        ratelimit=ratelimit,
        static=static,
        strict_json=strict_json,
        client_id=_install(keys / "client-id", b"client-id-0000000.access"),
        client_secret=_install(keys / "client-secret", b"s" * 32),
    )


def materialize(case: dict) -> dict:
    """The concrete case both sides decide: a lease case's issued and possibly mutated lease."""
    if case["domain"] != "lease":
        return case
    spec = case.pop("issue")
    signer = _STATE["oauth_broker"].BrokerLeaseSigner(
        (ROTATED_KEY, CURRENT_KEY) if spec["rotated"] else (CURRENT_KEY, PREVIOUS_KEY),
        clock=lambda: spec["issued_at"],
    )
    tokens = _STATE["oauth_broker"].OAuthTokens(spec["tokens"][0], spec["tokens"][1], 3600)
    lease = signer.issue(tokens, tuple(spec["scopes"]))
    if spec["mutation"]:
        rng = random.Random(spec["seed"])
        position = rng.randrange(len(lease))
        lease = lease[:position] + rng.choice("AZaz09_-.=١") + lease[position + 1 :]
    return {**case, "lease": lease}


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def _admission(pairs: list[tuple[str, str]], names: tuple[str, ...]) -> list[str] | None:
    keys = {key for key, _value in pairs}
    if len(pairs) != len(names) or keys != set(names):
        return None
    fields = dict(pairs)
    return [fields[name] for name in names]


def query(case: dict) -> str:
    text = case["query"]
    lenient = parse_qsl(text, keep_blank_values=True)
    try:
        strict = parse_qsl(text, keep_blank_values=True, strict_parsing=True, max_num_fields=7)
    except ValueError:
        strict = None
    start = _admission(lenient, ("state", "code_challenge", "scope", "callback"))
    if start is not None and start[3] not in {"loopback", "local-domain", "out-of-band"}:
        start = None
    callback = _admission(lenient, ("state", "code", "scope"))
    return _json([lenient, strict, start, callback])


class _Reply:
    def __init__(self, url: str) -> None:
        self.url = url

    def request(self, *, url: str, headers, body: bytes):
        payload = json.dumps({"authorization_url": self.url}).encode()
        return _STATE["oauth_broker"].BrokerResponse(200, "application/json", payload)


def authorization(case: dict) -> str:
    broker = _STATE["oauth_broker"]
    client = broker.NeuronOAuthClient(
        _Reply(case["url"]), client_id_path=_STATE["client_id"], client_secret_path=_STATE["client_secret"]
    )
    try:
        client.authorization(state=case["state"], code_challenge=case["challenge"], scopes=tuple(case["scopes"]))
    except broker.OAuthBrokerError:
        return "refuse"
    return "ok"


def lease(case: dict) -> str:
    broker = _STATE["oauth_broker"]
    signer = broker.BrokerLeaseSigner((CURRENT_KEY, PREVIOUS_KEY), clock=lambda: case["now"])
    scopes = None if case["scopes"] is None else tuple(case["scopes"])
    try:
        signer.verify(case["lease"], case["token"], scopes)
    except broker.OAuthBrokerError:
        return "refuse"
    return "ok"


def catalog(case: dict) -> str:
    document = base64.b64decode(case["document"])
    try:
        value = _STATE["strict_json"].loads(document)
        projected = _STATE["catalog"].project_catalog(value, case["locale"])
    except ValueError:
        return "refuse"
    return json.dumps(projected, separators=(",", ":"), sort_keys=True, ensure_ascii=False)


class _Request:
    def __init__(self, navigation: bool) -> None:
        self.headers = {"accept": "text/html"} if navigation else {}


def path(case: dict) -> str:
    response = _STATE["static"].static_files(case["path"], _Request(case["navigation"]))
    body = Path(response.path).read_bytes() if hasattr(response, "path") else response.body
    return _json([response.status_code, response.headers["cache-control"], body.decode("utf-8")])


def client_key(case: dict) -> str:
    ratelimit = _STATE["ratelimit"]
    try:
        proxies = ratelimit.trusted_proxies(case["proxies"])
    except ValueError:
        return _json(["refuse", None])
    try:
        key = ratelimit.client_key(case["peer"], case["forwarded"], proxies)
    except ratelimit.ClientAddressError:
        key = "refuse"
    return _json([[str(network) for network in proxies], key])


def request_id(case: dict) -> str:
    raw = case["values"][-1].encode("latin-1") if case["values"] else b""
    cleaned = _STATE["middleware"]._clean(raw)
    fresh = not _STATE["middleware"]._UNSAFE.sub("", raw.decode("latin-1"))[:200]
    return "fresh" if fresh else cleaned


def media(case: dict) -> str:
    static = _STATE["static"]
    return _json(
        [
            static.media_type(Path(case["name"])),
            static.entity_tag(case["mtime_ns"], case["size"]),
            static.last_modified(case["mtime_ns"]),
        ]
    )


DECIDE = {
    "query": query,
    "authorization": authorization,
    "lease": lease,
    "catalog": catalog,
    "path": path,
    "client_key": client_key,
    "request_id": request_id,
    "media": media,
}


def decide(case: dict) -> str:
    """The Python Store's canonical answer to one case."""
    return DECIDE[case["domain"]](case)
