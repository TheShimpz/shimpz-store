"""Same-origin Account factor ceremonies for one Hosted Power challenge."""

from __future__ import annotations

import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import authn, config
from app.access import mutation_origin_allowed, private_json
from app.config import MAX_AUTH_BODY_BYTES
from app.payloads import ClientPayloadError, read_bounded_json
from app.protocol.http.v1 import payload as team_contract
from app.protocol.http.v1.websocket import valid_challenge_id
from app.upstream import CONTROL_PLANE_TIMEOUT_SECONDS, call_bounded

router = APIRouter()

_BASE_FIELDS = frozenset({"team_id", "challenge_id"})
_BASE64URL = re.compile(r"[A-Za-z0-9_-]{1,4096}\Z")
_MAX_ASSURANCE_TTL_SECONDS = 300
_RP_ID = re.compile(
    r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z"
)


def _public_error(status: int) -> JSONResponse:
    safe_status = status if 400 <= status <= 599 else 502
    if safe_status in {401, 403}:
        detail = "authentication was not confirmed"
    elif safe_status == 429:
        detail = "authentication capacity reached; try again shortly"
    elif safe_status < 500:
        detail = "authentication request was rejected"
    else:
        detail = "authentication is temporarily unavailable"
    return private_json({"detail": detail}, safe_status)


def _binding(payload: dict, factor_field: str | None) -> dict[str, object]:
    expected = _BASE_FIELDS | ({factor_field} if factor_field is not None else set())
    if set(payload) != expected:
        raise ClientPayloadError(400, "invalid Power assurance request")
    team_id = team_contract.canonical_team_id(payload.get("team_id"))
    challenge_id = payload.get("challenge_id")
    if team_id is None or not valid_challenge_id(challenge_id):
        raise ClientPayloadError(400, "invalid Power assurance request")
    result: dict[str, object] = {"team_id": team_id, "challenge_id": challenge_id}
    if factor_field is not None:
        result[factor_field] = payload[factor_field]
    return result


def _handle_response(status: int, data: dict) -> JSONResponse:
    if status != 200:
        return _public_error(status)
    expires_in = data.get("expires_in")
    if (
        set(data) != {"version", "handle", "expires_in"}
        or data.get("version") != 1
        or team_contract.canonical_assurance_handle(data.get("handle")) is None
        or isinstance(expires_in, bool)
        or not isinstance(expires_in, int)
        or not 1 <= expires_in <= _MAX_ASSURANCE_TTL_SECONDS
    ):
        return _public_error(502)
    return private_json(data)


def _credential_descriptor(value: object) -> dict[str, str] | None:
    if (
        not isinstance(value, dict)
        or set(value) != {"id", "type"}
        or value.get("type") != "public-key"
        or not isinstance(value.get("id"), str)
        or _BASE64URL.fullmatch(value["id"]) is None
    ):
        return None
    return {"id": value["id"], "type": "public-key"}


def _options_response(status: int, data: dict) -> JSONResponse:
    if status != 200:
        return _public_error(status)
    expected = {"challenge", "timeout", "rpId", "allowCredentials", "userVerification"}
    descriptors = data.get("allowCredentials")
    projected = (
        [_credential_descriptor(value) for value in descriptors]
        if isinstance(descriptors, list) and 1 <= len(descriptors) <= 32
        else []
    )
    if (
        set(data) != expected
        or not isinstance(data.get("challenge"), str)
        or _BASE64URL.fullmatch(data["challenge"]) is None
        or isinstance(data.get("timeout"), bool)
        or not isinstance(data.get("timeout"), int)
        or not 1 <= data["timeout"] <= 300_000
        or not isinstance(data.get("rpId"), str)
        or _RP_ID.fullmatch(data["rpId"]) is None
        or data.get("userVerification") != "required"
        or not projected
        or any(value is None for value in projected)
    ):
        return _public_error(502)
    return private_json(
        {
            "challenge": data["challenge"],
            "timeout": data["timeout"],
            "rpId": data["rpId"],
            "allowCredentials": projected,
            "userVerification": "required",
        }
    )


async def _account_ceremony(
    request: Request,
    path: str,
    factor_field: str | None,
    *,
    options: bool = False,
) -> JSONResponse:
    if not mutation_origin_allowed(request.headers.get("origin")):
        return private_json({"detail": "origin is not allowed"}, 403)
    token, _, _ = await authn.authed_account_bounded(request)
    if not token:
        return private_json({"detail": "not authenticated"}, 401)
    payload = _binding(await read_bounded_json(request, MAX_AUTH_BODY_BYTES), factor_field)
    status, data = await call_bounded(
        authn.EXECUTOR,
        config.ACCOUNT_URL,
        "POST",
        path,
        {"token": token, **payload},
        extra={"X-Forwarded-For": authn.client_ip(request)},
        timeout=CONTROL_PLANE_TIMEOUT_SECONDS,
    )
    if not isinstance(data, dict):
        return _public_error(502)
    return _options_response(status, data) if options else _handle_response(status, data)


@router.post("/api/security/power-assurance/password")
async def password(request: Request) -> JSONResponse:
    return await _account_ceremony(
        request,
        "/v1/security/power-assurance/password",
        "password",
    )


@router.post("/api/security/power-assurance/totp")
async def totp(request: Request) -> JSONResponse:
    return await _account_ceremony(
        request,
        "/v1/security/power-assurance/totp",
        "code",
    )


@router.post("/api/security/power-assurance/webauthn/options")
async def webauthn_options(request: Request) -> JSONResponse:
    return await _account_ceremony(
        request,
        "/v1/security/power-assurance/webauthn/options",
        None,
        options=True,
    )


@router.post("/api/security/power-assurance/webauthn/confirm")
async def webauthn_confirm(request: Request) -> JSONResponse:
    return await _account_ceremony(
        request,
        "/v1/security/power-assurance/webauthn/confirm",
        "credential",
    )
