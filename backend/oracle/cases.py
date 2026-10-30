"""Seeded case generators of the Store differential, one per domain; each case is a JSON object with its domain."""

import base64
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = json.loads((ROOT / "src" / "catalog" / "project" / "catalog.json").read_text(encoding="utf-8"))
LOCALES = ("de", "en", "es", "fr", "it", "ja", "pt", "zh")
SCOPES = ("dns.read", "dns.write", "offline_access", "zone.read")
QUERY_ALPHABET = "abcdeSZ09_-.~+%=&/:;!$'()*,@[]? \"#<>^`{|}\\"
QUERY_WORDS = ("state", "code_challenge", "scope", "callback", "code", "loopback", "local-domain", "out-of-band")
URL_ALPHABET = "AZaz09_.~:/%?=@[]!$&'()*+,;-#\t \"<>\\^`{|}\x7fé"
BINDING_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
LEASE_ALPHABET = BINDING_ALPHABET + ".=+/ ١\n"
TOKENS = ("access-token-0001", "refresh-token-001", "another-token-01", "access-token-0002")
PATH_SEGMENTS = (
    "en",
    "pt",
    "fr",
    "de",
    "404",
    "404.html",
    "en.html",
    "index",
    "index.html",
    "_app",
    "immutable",
    "a.js",
    "version.json",
    "robots.txt",
    "favicon.ico",
    "deep",
    "x",
    "inside-link",
    "outside-link",
    "dir",
    "dir.html",
    "inner.txt",
    "a b",
    "é",
    "..",
    ".",
    "",
    "secret.txt",
    "build",
    "%2e%2e",
    "A.JS",
    "missing",
)
CIDRS = (
    "10.0.0.0/24",
    "10.0.0.0/8",
    "2001:db8::/32",
    "0.0.0.0/0",
    "::/0",
    "::ffff:10.0.0.0/120",
    "192.0.2.7/32",
    "10.0.0.1/24",
    "010.0.0.0/8",
    "10.0.0.0/024",
    "10.0.0.0/33",
    "2001:db8::/129",
    "fe80::%eth0/64",
    "tunnel",
    "10.0.0.0",
    "10.0.0.0/255.0.0.0",
    "1:2:3:4:5:6:7::/128",
    "::1.2.3.4/128",
    "1::2:3:4:5:6:7/128",
    "",
    "1:2:3:4::5:6:7:8/128",
    "::ffff:1.2.3.04/128",
    "2001:DB8::/32",
)
ADDRESSES = (
    "10.0.0.2",
    "10.0.0.255",
    "192.0.2.7",
    "203.0.113.5",
    "0.0.0.0",
    "255.255.255.255",
    "::ffff:10.0.0.9",
    "2001:db8:1:2:3:4:5:6",
    "2001:db8::1",
    "::",
    "::1",
    "fe80::1",
    "::ffff:203.0.113.5",
    "::1.2.3.4",
    "1:2:3:4:5:6:7::",
    "1::2:3:4:5:6:7",
    "2001:DB8:0:0:8:800:200C:417A",
)
FORWARDED_NOISE = (
    "203.0.113.05",
    " 203.0.113.5",
    "203.0.113.5 ",
    "fe80::1%eth0",
    "2001:db8::1%1",
    "203.0.113.5, 198.51.100.1",
    "1.2.3",
    "1.2.3.4.5",
    "256.1.1.1",
    "::ffff:1.2.3.04",
    "1:2:3:4::5:6:7:8",
    "::1:2:3:4:5:6:7:8",
    "tunnel",
    "0x7f.0.0.1",
    "2001:db8::g",
    "",
    "é",
    "1.2.3.4 ",
)
MEDIA_NAMES = (
    "a.html",
    "a.HTML",
    "b.css",
    "c.js",
    "d.json",
    "e.png",
    "f.svg",
    "g.txt",
    "h.xml",
    "i.woff",
    "j.woff2",
    "k.ico",
    "l.webmanifest",
    "m.htm",
    "n",
    ".hidden",
    "a.",
    "a..js",
    "a.tar.gz",
    "noext.",
    ".js",
    "..",
    "a.Js",
    "é.png",
    "a.jıs",
    "a.webManifest",
)


def _pick(rng: random.Random, items):
    return items[rng.randrange(len(items))]


def _text(rng: random.Random, alphabet: str, longest: int) -> str:
    return "".join(_pick(rng, alphabet) for _ in range(rng.randrange(longest + 1)))


def _binding(rng: random.Random) -> str:
    return "".join(_pick(rng, BINDING_ALPHABET) for _ in range(43))


def _scopes(rng: random.Random) -> list[str]:
    chosen = sorted(rng.sample(SCOPES, rng.randrange(1, len(SCOPES) + 1)))
    if rng.random() < 0.05:
        chosen.reverse()
    if rng.random() < 0.02:
        chosen.append(chosen[0])
    if rng.random() < 0.02:
        chosen = [*chosen, "account.read"]
    return chosen


def query(rng: random.Random) -> dict:
    """A request query: noise, or exact start and callback field sets with mutations."""
    if rng.random() < 0.5:
        parts = []
        for _ in range(rng.randrange(7)):
            name = _pick(rng, QUERY_WORDS) if rng.random() < 0.7 else _text(rng, QUERY_ALPHABET, 6)
            value = _pick(rng, QUERY_WORDS) if rng.random() < 0.3 else _text(rng, QUERY_ALPHABET, 8)
            separator = "=" if rng.random() < 0.85 else ""
            parts.append(f"{name}{separator}{value}")
        text = "&".join(parts)
    else:
        text = _text(rng, QUERY_ALPHABET + "&&==", 40)
    return {"domain": "query", "query": text}


def _consent(rng: random.Random, state: str, challenge: str, scopes: list[str]) -> str:
    fields = [
        ("response_type", "code"),
        ("client_id", _text(rng, "abcdef0123456789-", 20) or "client-1"),
        ("redirect_uri", "https://shimpz.com/api/oauth/cloudflare/callback"),
        ("state", state),
        ("code_challenge", challenge),
        ("code_challenge_method", "S256"),
        ("scope", "+".join(sorted(set(scopes) & set(SCOPES))) or "dns.read"),
    ]
    rng.shuffle(fields)
    if rng.random() < 0.1:
        fields.append(_pick(rng, fields))
    if rng.random() < 0.1:
        fields.pop(rng.randrange(len(fields)))
    return "https://dash.cloudflare.com/oauth2/auth?" + "&".join(f"{name}={value}" for name, value in fields)


def _mutate(rng: random.Random, text: str, alphabet: str) -> str:
    for _ in range(rng.randrange(1, 4)):
        position = rng.randrange(len(text) + 1)
        operation = rng.randrange(3)
        if operation == 0:
            text = text[:position] + _pick(rng, alphabet) + text[position:]
        elif operation == 1:
            text = text[:position] + text[position + 1 :]
        else:
            text = text[:position] + _pick(rng, alphabet) + text[position + 1 :]
    return text


def authorization(rng: random.Random) -> dict:
    """An authorization URL for a state, challenge, and scopes: exact, mutated, or oversized."""
    state, challenge, scopes = _binding(rng), _binding(rng), _scopes(rng)
    url = _consent(rng, state, challenge, scopes)
    roll = rng.random()
    if roll < 0.4:
        url = _mutate(rng, url, URL_ALPHABET)
    elif roll < 0.45:
        url = url + "&x=" + "x" * rng.randrange(4000, 4200)
    elif roll < 0.5:
        url = url.replace(
            "https://dash.cloudflare.com",
            _pick(
                rng, ("HTTPS://dash.cloudflare.com", "https://dash.cloudflare.com:443", "https://u@dash.cloudflare.com")
            ),
        )
    elif roll < 0.55:
        url = url.replace(state, _pick(rng, ("%" + "41" * 1, state[:42], state + "A")), 1)
    return {"domain": "authorization", "url": url, "state": state, "challenge": challenge, "scopes": scopes}


def lease(rng: random.Random) -> dict:
    """A lease the Python signer issues for chosen tokens, scopes, key order, and time, then possibly mutated."""
    issued_at = rng.randrange(1_000_000_000, 9_000_000_000)
    lease_spec = {
        "tokens": [_pick(rng, TOKENS), _pick(rng, TOKENS)],
        "scopes": sorted(rng.sample(SCOPES, rng.randrange(1, 5))),
        "issued_at": issued_at,
        "rotated": rng.random() < 0.3,
        "mutation": rng.random() < 0.35,
        "seed": rng.randrange(2**32),
    }
    now = issued_at + _pick(rng, (0, 1, 366 * 86400 - 1, 366 * 86400, 366 * 86400 + 1, -5, rng.randrange(10**8)))
    scopes = None if rng.random() < 0.4 else _scopes(rng)
    return {"domain": "lease", "issue": lease_spec, "token": _pick(rng, TOKENS), "scopes": scopes, "now": now}


def _mutate_value(rng: random.Random, value):
    if isinstance(value, dict) and value:
        key = _pick(rng, sorted(value))
        roll = rng.random()
        if roll < 0.15:
            del value[key]
        elif roll < 0.25:
            value[_pick(rng, ("extra", "name", "id", key + "x"))] = 1
        else:
            value[key] = _mutate_value(rng, value[key])
        return value
    if isinstance(value, list) and value:
        roll = rng.random()
        if roll < 0.2:
            value.append(value[rng.randrange(len(value))])
        elif roll < 0.35:
            value.pop(rng.randrange(len(value)))
        elif roll < 0.45:
            value.reverse()
        else:
            index = rng.randrange(len(value))
            value[index] = _mutate_value(rng, value[index])
        return value
    return _replacement(rng, value)


def _replacement(rng: random.Random, value):
    choices = (
        None,
        True,
        1,
        1.5,
        -1,
        "",
        " ",
        "x" * rng.randrange(1, 600),
        "é",
        "é",
        "a‮b",
        "a\nb",
        " x",
        "x ",
        "Hello",
        "@shimpz",
        "https://example.com/",
        "sha256:" + "a" * 64,
        "linux/amd64",
        "read_only",
        "mutating",
        "approval",
        "input:text",
        "auth:totp",
        "password",
        "api-token",
        [],
        {},
    )
    if isinstance(value, str) and rng.random() < 0.5:
        return _mutate(rng, value, "aZ09 .-_:/@é́\t‮")
    return _pick(rng, choices)


def catalog(rng: random.Random) -> dict:
    """The fixture catalog with up to three mutations, in a chosen locale."""
    document = json.loads(json.dumps(CATALOG))
    locale = _pick(rng, (*LOCALES, "pt", "pt", "xx"))
    document["locale"] = locale if rng.random() < 0.9 else _pick(rng, LOCALES)
    for _ in range(rng.randrange(4)):
        document = _mutate_value(rng, document)
    text = json.dumps(document, ensure_ascii=rng.random() < 0.5)
    return {"domain": "catalog", "document": base64.b64encode(text.encode("utf-8")).decode(), "locale": locale}


def path(rng: random.Random) -> dict:
    """A decoded static path built from the build's names, traversal, controls, and noise."""
    segments = [_pick(rng, PATH_SEGMENTS) for _ in range(rng.randrange(1, 5))]
    text = "/".join(segments)
    roll = rng.random()
    if roll < 0.1:
        text = "/" + text
    elif roll < 0.2:
        text += "/"
    elif roll < 0.25:
        text += _pick(rng, ("\x00", "\n", "\t", "\x1f", "\\", "%00"))
    return {"domain": "path", "path": text, "navigation": rng.random() < 0.5}


def client_key(rng: random.Random) -> dict:
    """A peer, its forwarded client values, and a trusted-proxy configuration."""
    proxies = None if rng.random() < 0.2 else ",".join(_pick(rng, CIDRS) for _ in range(rng.randrange(1, 3)))
    forwarded = [
        _pick(rng, ADDRESSES) if rng.random() < 0.6 else _pick(rng, FORWARDED_NOISE)
        for _ in range(_pick(rng, (0, 1, 1, 1, 2)))
    ]
    return {"domain": "client_key", "peer": _pick(rng, ADDRESSES), "forwarded": forwarded, "proxies": proxies}


def request_id(rng: random.Random) -> dict:
    """Up to three `X-Request-ID` values of header bytes, as Latin-1 text."""
    alphabet = "".join(chr(code) for code in (*range(0x20, 0x7F), *range(0x80, 0x100), 9))
    values = []
    for _ in range(rng.randrange(4)):
        if rng.random() < 0.3:
            values.append(_text(rng, BINDING_ALPHABET + ".", rng.randrange(1, 260)))
        else:
            values.append(_text(rng, alphabet, 30))
    return {"domain": "request_id", "values": values}


def media(rng: random.Random) -> dict:
    """A file name, mtime in nanoseconds, and size."""
    mtime = _pick(
        rng,
        (
            0,
            -1,
            -1_000_000_000,
            253402300799_999_999_999,
            253402300800_000_000_000,
            1_700_000_000_999_999_999,
            rng.randrange(-(2**63), 2**63),
            rng.randrange(0, 253402300800 * 10**9),
        ),
    )
    size = _pick(rng, (0, 1, 15, rng.randrange(2**63)))
    return {"domain": "media", "name": _pick(rng, MEDIA_NAMES), "mtime_ns": mtime, "size": size}


GENERATORS = {
    "query": query,
    "authorization": authorization,
    "lease": lease,
    "catalog": catalog,
    "path": path,
    "client_key": client_key,
    "request_id": request_id,
    "media": media,
}
