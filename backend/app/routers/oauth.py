"""Closed Cloudflare OAuth broker routes."""

from __future__ import annotations

import asyncio
import functools
import html
import secrets

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from app.concurrency import BoundedThreadPoolExecutor
from app.config import OAUTH_QUEUE_MAX, OAUTH_WORKER_THREADS, PRIVATE_NO_STORE_HEADERS
from app.oauth_broker import SCOPES, OAuthBroker, OAuthBrokerError, OAuthOutOfBand, OAuthRedirect
from app.payloads import ClientPayloadError, read_bounded_json

log = structlog.get_logger()
router = APIRouter()
_EXECUTOR = BoundedThreadPoolExecutor(
    max_workers=OAUTH_WORKER_THREADS,
    max_outstanding=OAUTH_WORKER_THREADS + OAUTH_QUEUE_MAX,
    thread_name_prefix="store-oauth",
)
_BROKER = OAuthBroker()


async def _run_bounded(fn, /, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_EXECUTOR, fn, *args)


def _redirect(location: str) -> RedirectResponse:
    return RedirectResponse(
        location,
        status_code=303,
        headers={
            "Cache-Control": "private, no-store",
            "Referrer-Policy": "no-referrer",
        },
    )


def _completion_page(completion: OAuthOutOfBand) -> HTMLResponse:
    nonce = secrets.token_urlsafe(18)
    code = html.escape(completion.completion_code, quote=True)
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Finish in Shimpz Admin</title>
  <style nonce="{nonce}">
    :root {{ color-scheme: dark; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
    * {{ box-sizing: border-box; }}
    body {{ min-height: 100vh; margin: 0; display: grid; place-items: center; background: #000; color: #f4f4f5; }}
    main {{ width: min(50rem, calc(100% - 2rem)); border: 1px solid #303036; padding: clamp(1.5rem, 5vw, 3rem); }}
    p {{ color: #a1a1aa; line-height: 1.6; }}
    label {{ display: block; margin: 2rem 0 .6rem; color: #00e5f0; font-size: .8rem; letter-spacing: .12em; }}
    input {{ width: 100%; padding: 1rem; border: 1px solid #3f3f46; background: #09090b; color: #fff; font: inherit; }}
    button {{ width: 100%; margin-top: .75rem; padding: 1rem; border: 0; background: #00e5f0; color: #000;
      font: 700 1rem inherit; cursor: pointer; }}
    .warning {{ color: #f4f4f5; }}
  </style>
</head>
<body>
  <main>
    <p>INTEGRATION // ONE-TIME COMPLETION</p>
    <h1>Finish in your original Shimpz Admin tab.</h1>
    <p>Copy this short-lived code, return to the tab that started Cloudflare authorization, and paste it there.</p>
    <label for="completion-code">COMPLETION CODE</label>
    <input id="completion-code" value="{code}" readonly autocomplete="off" spellcheck="false">
    <button id="copy-code" type="button">COPY CODE</button>
    <p class="warning">Do not paste this code into chat or another site. It contains no provider token and works
      only with the Admin session that started this authorization.</p>
  </main>
  <script nonce="{nonce}">
    const input = document.getElementById('completion-code');
    const button = document.getElementById('copy-code');
    button.addEventListener('click', async () => {{
      input.select();
      try {{
        await navigator.clipboard.writeText(input.value);
        button.textContent = 'COPIED';
      }} catch (_error) {{
        button.textContent = 'SELECTED — COPY MANUALLY';
      }}
    }});
  </script>
</body>
</html>"""
    return HTMLResponse(
        document,
        headers={
            "Cache-Control": "private, no-store",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": (
                "default-src 'none'; "
                f"style-src 'nonce-{nonce}'; script-src 'nonce-{nonce}'; "
                "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
            ),
            "Cross-Origin-Opener-Policy": "same-origin",
            "X-Content-Type-Options": "nosniff",
        },
    )


async def _body(request: Request, fields: frozenset[str]) -> dict:
    if request.headers.get("origin") is not None or request.headers.get("content-type") != "application/json":
        raise ClientPayloadError(403, "OAuth broker request is forbidden")
    if request.headers.get("content-length") is None:
        raise ClientPayloadError(411, "OAuth broker request length is required")
    payload = await read_bounded_json(request, 32 * 1024)
    if set(payload) != fields:
        raise ClientPayloadError(400, "OAuth broker request is invalid")
    return payload


def _failure(operation: str, status: int = 400) -> JSONResponse:
    log.warning("oauth_broker_rejected", operation=operation)
    return JSONResponse(
        {"detail": "OAuth broker operation failed"},
        status_code=status,
        headers=PRIVATE_NO_STORE_HEADERS,
    )


@router.get("/api/oauth/cloudflare/start")
async def cloudflare_start(request: Request) -> Response:
    pairs = list(request.query_params.multi_items())
    keys = {key for key, _value in pairs}
    required = {"state", "code_challenge", "scope", "callback"}
    if len(pairs) != 4 or keys != required:
        return _failure("start")
    fields = dict(pairs)
    callback_mode = fields["callback"]
    if callback_mode not in {"loopback", "hosted", "out-of-band"}:
        return _failure("start")
    try:
        location = await _run_bounded(
            functools.partial(
                _BROKER.start,
                local_state=fields["state"],
                local_code_challenge=fields["code_challenge"],
                callback_mode=callback_mode,
                scopes=fields["scope"].split(" "),
            ),
        )
    except OAuthBrokerError:
        return _failure("start", 502)
    return _redirect(location)


@router.get("/api/oauth/cloudflare/callback")
async def cloudflare_callback(request: Request) -> Response:
    pairs = list(request.query_params.multi_items())
    if len(pairs) != 3 or {key for key, _value in pairs} != {"state", "code", "scope"}:
        return _failure("callback")
    fields = dict(pairs)
    if tuple(fields["scope"].split(" ")) != SCOPES:
        return _failure("callback")
    try:
        completion = await _run_bounded(functools.partial(_BROKER.callback, state=fields["state"], code=fields["code"]))
    except OAuthBrokerError:
        return _failure("callback", 502)
    if isinstance(completion, OAuthRedirect):
        return _redirect(completion.location)
    if isinstance(completion, OAuthOutOfBand):
        return _completion_page(completion)
    return _failure("callback", 502)


async def _post(request: Request, operation: str, fields: frozenset[str]) -> JSONResponse:
    try:
        payload = await _body(request, fields)
        if operation == "claim":
            result = await _run_bounded(
                functools.partial(
                    _BROKER.claim,
                    claim=payload["claim"],
                    state=payload["state"],
                    code_verifier=payload["code_verifier"],
                ),
            )
        elif operation == "refresh":
            result = await _run_bounded(
                functools.partial(
                    _BROKER.refresh,
                    refresh_token=payload["refresh_token"],
                    lease=payload["broker_lease"],
                    scopes=payload["scopes"],
                ),
            )
        elif operation == "revoke":
            await _run_bounded(
                functools.partial(
                    _BROKER.revoke,
                    token=payload["token"],
                    lease=payload["broker_lease"],
                ),
            )
            result = {"revoked": True}
        else:
            raise OAuthBrokerError("OAuth broker operation is unavailable")
    except ClientPayloadError as exc:
        return _failure(operation, exc.status)
    except OAuthBrokerError:
        return _failure(operation, 502)
    return JSONResponse(result, headers=PRIVATE_NO_STORE_HEADERS)


@router.post("/api/oauth/cloudflare/claim")
async def cloudflare_claim(request: Request) -> JSONResponse:
    return await _post(request, "claim", frozenset({"claim", "state", "code_verifier"}))


@router.post("/api/oauth/cloudflare/refresh")
async def cloudflare_refresh(request: Request) -> JSONResponse:
    return await _post(request, "refresh", frozenset({"refresh_token", "broker_lease", "scopes"}))


@router.post("/api/oauth/cloudflare/revoke")
async def cloudflare_revoke(request: Request) -> JSONResponse:
    return await _post(request, "revoke", frozenset({"token", "broker_lease"}))
