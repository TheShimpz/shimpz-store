"""Public account authentication routes."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import authn
from app.access import mutation_origin_allowed, private_json, require_json_mutation
from app.concurrency import ExecutorSaturatedError
from app.config import ACCOUNT_COOKIE, MAX_AUTH_BODY_BYTES
from app.payloads import ClientPayloadError, read_bounded_json
from app.upstream import CONTROL_PLANE_TIMEOUT_SECONDS, call_bounded

router = APIRouter()


async def _bounded_call(*args, **kwargs) -> tuple[int, dict]:
    return await call_bounded(authn.EXECUTOR, *args, **kwargs)


async def _login(request: Request) -> JSONResponse:
    # A cross-site login would sign the browser into the attacker's account (login CSRF).
    require_json_mutation(request)
    payload = await read_bounded_json(request, MAX_AUTH_BODY_BYTES)
    status, data = await _bounded_call(
        authn.ACCOUNT_URL,
        "POST",
        "/v1/login",
        {"username": payload.get("username"), "password": payload.get("password")},
        extra={"X-Forwarded-For": authn.client_ip(request)},
        timeout=CONTROL_PLANE_TIMEOUT_SECONDS,
    )
    body = {"account_id": data.get("account_id"), "username": data.get("username")} if status == 200 else data
    response = private_json(body, status)
    if status == 200 and data.get("token"):
        authn.set_cookie(response, data["token"])
    return response


@router.post("/api/login")
async def login(request: Request) -> JSONResponse:
    return await _login(request)


async def _revoke_session(token: str) -> int:
    """Revoke the exact Account session; an absent or already-revoked session is a successful outcome."""
    if not token:
        return 200
    try:
        status, _ = await _bounded_call(
            authn.ACCOUNT_URL,
            "POST",
            "/v1/logout",
            {"token": token},
            timeout=CONTROL_PLANE_TIMEOUT_SECONDS,
        )
    except ExecutorSaturatedError:
        return 429
    return status


@router.post("/api/logout")
async def logout(request: Request) -> JSONResponse:
    if not mutation_origin_allowed(request.headers.get("origin")):
        raise ClientPayloadError(403, "forbidden origin")
    status = await _revoke_session(request.cookies.get(ACCOUNT_COOKIE, ""))
    if status == 200:
        response = private_json({"ok": True})
    else:
        # The browser forgets the cookie, so a retry cannot reach this session; say revocation stays unconfirmed.
        response = private_json(
            {"detail": "signed out of this browser, but Account did not confirm revoking the session"},
            429 if status == 429 else 502,
        )
    response.delete_cookie(ACCOUNT_COOKIE, path="/")
    return response


@router.get("/api/me")
async def me(request: Request) -> JSONResponse:
    _, account_id, username = await authn.authed_account_bounded(request)
    return private_json(
        {
            "authenticated": bool(account_id),
            "account_id": account_id or None,
            "username": username or None,
        }
    )
