"""Closed Cloudflare OAuth broker routes."""

from __future__ import annotations

import asyncio
import functools

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from app.concurrency import BoundedThreadPoolExecutor
from app.config import OAUTH_QUEUE_MAX, OAUTH_WORKER_THREADS, PRIVATE_NO_STORE_HEADERS
from app.oauth_broker import SCOPES, OAuthBroker, OAuthBrokerError
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
    required = {"state", "code_challenge", "scope"}
    if len(pairs) not in {3, 4} or keys not in {frozenset(required), frozenset({*required, "callback"})}:
        return _failure("start")
    fields = dict(pairs)
    callback_mode = fields.get("callback", "loopback")
    if callback_mode not in {"loopback", "hosted"}:
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
        location = await _run_bounded(functools.partial(_BROKER.callback, state=fields["state"], code=fields["code"]))
    except OAuthBrokerError:
        return _failure("callback", 502)
    return _redirect(location)


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
