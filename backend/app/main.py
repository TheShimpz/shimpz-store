"""Shimpz storefront serve — one FastAPI process serves the prerendered SvelteKit build (best SEO) AND
the account-authenticated control surface (/api): the shimpz.com loop = signup/login → my Capsules →
create/select → install. It holds NO privileged secret: it PROXIES auth to the `accounts` service and
FORWARDS the user's account token to the socket-holding `capsule-driver`, which is the sole enforcer
(it verifies the token + scopes every op to the account's own Capsules). Reached over the Space's
internal nets (accounts_net + capsuledriver_net). Stdlib http.client for the proxy hops."""

from __future__ import annotations

import http.client
import json as jsonlib
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response

from app.logconf import setup

setup("shimpz-store")
log = structlog.get_logger()

BUILD = Path(os.environ.get("SHIMPZ_STORE_BUILD", "/app/build"))
ACCOUNTS_URL = os.environ.get("SHIMPZ_ACCOUNTS_URL", "http://accounts:7079")
CAPSULEDRIVER_URL = os.environ.get("SHIMPZ_CAPSULEDRIVER_URL", "http://capsule-driver:7077")
ACCOUNT_COOKIE = "shimpz_account"
COOKIE_MAX_AGE = 7 * 24 * 3600

app = FastAPI(title="shimpz-store", docs_url=None, redoc_url=None, openapi_url=None)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    # Fail-loud: full structured trace in the logs, generic 500 to the caller. Never swallow.
    log.exception("unhandled_exception", path=request.url.path)
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


# ── proxy helpers (the store forwards; it holds no privileged secret) ──────────
def _call(base: str, method: str, path: str, payload: dict | None = None, account_token: str = "") -> tuple[int, dict]:
    parsed = urlparse(base)
    headers: dict[str, str] = {}
    body = None
    if payload is not None:
        body = jsonlib.dumps(payload)
        headers["Content-Type"] = "application/json"
    if account_token:
        headers["X-Shimpz-Account"] = account_token
    conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=180)
    try:
        conn.request(method, path, body, headers)
        resp = conn.getresponse()
        raw = resp.read()
        return resp.status, (jsonlib.loads(raw) if raw else {})
    except (OSError, jsonlib.JSONDecodeError) as exc:
        log.warning("proxy_unreachable", base=base, path=path, error=str(exc))
        return 502, {"detail": "the Space is unreachable"}
    finally:
        conn.close()


def _set_cookie(resp: JSONResponse, token: str) -> None:
    resp.set_cookie(
        ACCOUNT_COOKIE, token, max_age=COOKIE_MAX_AGE, httponly=True, samesite="strict", secure=True, path="/"
    )


def _authed_account(request: Request) -> tuple[str, str]:
    """(account_token, account_id) for a valid cookie, else ('', ''). Verified against the accounts service."""
    token = request.cookies.get(ACCOUNT_COOKIE, "")
    if not token:
        return "", ""
    status, data = _call(ACCOUNTS_URL, "POST", "/v1/verify", {"token": token})
    return (token, data["account_id"]) if status == 200 and data.get("account_id") else ("", "")


def _cid_for(account_id: str, name: str) -> str:
    """A globally-unique, Docker/PG-safe capsule id from (account, name) — so two accounts can both name
    a Capsule 'workspace' without colliding. The display name is kept separately (the capsule.owner/name)."""
    slug = re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_")[:28]
    return f"{account_id[:8]}_{slug}".strip("_")[:40]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ── account auth (proxied to the `accounts` identity service) ──────────────────
@app.post("/api/signup")
def signup(payload: dict) -> JSONResponse:
    status, data = _call(ACCOUNTS_URL, "POST", "/v1/signup", {"username": payload.get("username"), "password": payload.get("password")})
    body = {"account_id": data.get("account_id"), "username": data.get("username")} if status == 200 else data
    resp = JSONResponse(body, status_code=status)
    if status == 200 and data.get("token"):
        _set_cookie(resp, data["token"])
        log.info("signup", username=data.get("username"))
    return resp


@app.post("/api/login")
def login(payload: dict) -> JSONResponse:
    status, data = _call(ACCOUNTS_URL, "POST", "/v1/login", {"username": payload.get("username"), "password": payload.get("password")})
    body = {"account_id": data.get("account_id"), "username": data.get("username")} if status == 200 else data
    resp = JSONResponse(body, status_code=status)
    if status == 200 and data.get("token"):
        _set_cookie(resp, data["token"])
    return resp


@app.post("/api/logout")
def logout() -> JSONResponse:
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(ACCOUNT_COOKIE, path="/")
    return resp


@app.get("/api/me")
def me(request: Request) -> JSONResponse:
    _, account_id = _authed_account(request)
    return JSONResponse({"authenticated": bool(account_id), "account_id": account_id or None})


# ── Capsules (forward the user's token; capsule-driver is the enforcer) ────────
@app.get("/api/capsules")
def capsules_list(request: Request) -> JSONResponse:
    token, _ = _authed_account(request)
    if not token:
        return JSONResponse({"detail": "not authenticated"}, status_code=401)
    status, data = _call(CAPSULEDRIVER_URL, "GET", "/v1/capsules", account_token=token)
    return JSONResponse(data, status_code=status)


@app.post("/api/capsules")
def capsules_create(request: Request, payload: dict) -> JSONResponse:
    token, account_id = _authed_account(request)
    if not token:
        return JSONResponse({"detail": "not authenticated"}, status_code=401)
    name = str((payload or {}).get("name", "")).strip()
    cid = _cid_for(account_id, name)
    if not name or not cid.strip("_"):
        return JSONResponse({"detail": "bad capsule name"}, status_code=400)
    status, data = _call(CAPSULEDRIVER_URL, "POST", f"/v1/capsules/{cid}/create", {"name": name}, account_token=token)
    return JSONResponse(data, status_code=status)


@app.delete("/api/capsules/{cid}")
def capsules_destroy(request: Request, cid: str) -> JSONResponse:
    token, _ = _authed_account(request)
    if not token:
        return JSONResponse({"detail": "not authenticated"}, status_code=401)
    status, data = _call(CAPSULEDRIVER_URL, "DELETE", f"/v1/capsules/{cid}", account_token=token)
    return JSONResponse(data, status_code=status)


@app.post("/api/capsules/{cid}/install")
def capsule_install(request: Request, cid: str, payload: dict) -> JSONResponse:
    """P4 marketplace GATE: installing a (third-party) app requires a VALID Shimpz account AND ownership
    of the target Capsule. The account is verified and the ownership is confirmed by the capsule-driver
    (the forwarded token returns the Capsule only if it's the account's). The structured log line is the
    durable record; the actual per-Capsule app-container DEPLOY is the SDK/app-packaging layer (deferred,
    see docs/decisions/0002-capsules.md). Self-hosters validate the account against shimpz.com the same way."""
    token, account_id = _authed_account(request)
    if not token:
        return JSONResponse({"detail": "not authenticated"}, status_code=401)
    app_id = str((payload or {}).get("app", "")).strip()
    if not app_id.replace("-", "").isalnum():
        return JSONResponse({"detail": "bad app id"}, status_code=400)
    status, _ = _call(CAPSULEDRIVER_URL, "GET", f"/v1/capsules/{cid}/status", account_token=token)
    if status != 200:  # 404 = not yours / doesn't exist (the driver's owner-scoping)
        return JSONResponse({"detail": "capsule not found"}, status_code=404)
    log.info("app_install_requested", account=account_id, capsule=cid, app=app_id)
    return JSONResponse({"status": "installing", "app": app_id, "capsule": cid})


# ── static: serve the prerendered SvelteKit build (adapter-static writes <route>.html + assets) ──
def _resolve(rel: str) -> Path | None:
    rel = rel.strip("/")
    if ".." in rel.split("/"):  # no traversal out of BUILD
        return None
    for cand in (BUILD / rel, BUILD / f"{rel}.html", BUILD / rel / "index.html"):
        if cand.is_file():
            return cand
    return None


@app.get("/{path:path}")
def static_files(path: str) -> Response:
    hit = _resolve(path)
    if hit:
        return FileResponse(hit)
    # unknown path → the prerendered root (a redirect to /en); 404 status so bots don't index junk
    root = BUILD / "index.html"
    if root.is_file():
        return FileResponse(root, status_code=404)
    return PlainTextResponse("not found", status_code=404)
