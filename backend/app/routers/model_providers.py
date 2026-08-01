"""Account-scoped model credential routes."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import authn, config
from app.concurrency import run_bounded
from app.control import EXECUTOR as CONTROL_EXECUTOR
from app.inference import provider as canonical_provider
from app.payloads import read_bounded_json
from app.upstream import CONTROL_PLANE_TIMEOUT_SECONDS, call, call_bounded

log = structlog.get_logger()
router = APIRouter()

MAX_CREDENTIAL_BODY_BYTES = 72 * 1024


@router.get("/api/model-providers")
async def model_providers_list(request: Request) -> JSONResponse:
    token, _, _ = await authn.authed_account_bounded(request)
    if not token:
        return JSONResponse({"detail": "not authenticated"}, status_code=401)
    status, data = await call_bounded(
        authn.EXECUTOR,
        config.ACCOUNT_URL,
        "POST",
        "/v1/model-providers/list",
        {"token": token},
        extra={"X-Forwarded-For": authn.client_ip(request)},
        timeout=CONTROL_PLANE_TIMEOUT_SECONDS,
    )
    if status != 200 or not isinstance(data, dict):
        return JSONResponse(data, status_code=status)
    providers = data.get("model_providers")
    if not isinstance(providers, list):
        return JSONResponse({"detail": "invalid model provider inventory"}, status_code=502)
    return JSONResponse({"providers": providers})


@router.post("/api/model-providers/{provider}")
async def model_provider_upsert(request: Request, provider: str) -> JSONResponse:
    token, _, _ = await authn.authed_account_bounded(request)
    if not token:
        return JSONResponse({"detail": "not authenticated"}, status_code=401)
    provider_value = canonical_provider(provider)
    if provider_value is None:
        return JSONResponse({"detail": "unsupported model provider"}, status_code=400)
    payload = await read_bounded_json(request, MAX_CREDENTIAL_BODY_BYTES)
    if set(payload) != {"auth_type", "secret"}:
        return JSONResponse({"detail": "credential requires auth_type and secret"}, status_code=400)
    auth_type = str(payload.get("auth_type") or "").strip().lower()
    secret = payload.get("secret")
    if auth_type != "api_key" or not isinstance(secret, str):
        return JSONResponse({"detail": "invalid model provider credential"}, status_code=400)
    status, data = await call_bounded(
        authn.EXECUTOR,
        config.ACCOUNT_URL,
        "POST",
        "/v1/model-providers/upsert",
        {
            "token": token,
            "provider": provider_value,
            "auth_type": auth_type,
            "secret": secret,
        },
        {"X-Forwarded-For": authn.client_ip(request)},
        timeout=CONTROL_PLANE_TIMEOUT_SECONDS,
    )
    log.info("model_provider_upsert", provider=provider_value, status=status)
    return JSONResponse(data, status_code=status)


@router.delete("/api/model-providers/{provider}")
async def model_provider_delete(request: Request, provider: str) -> JSONResponse:
    token, _, _ = await authn.authed_account_bounded(request)
    if not token:
        return JSONResponse({"detail": "not authenticated"}, status_code=401)
    provider_value = canonical_provider(provider)
    if provider_value is None:
        return JSONResponse({"detail": "unsupported model provider"}, status_code=400)
    return await run_bounded(
        CONTROL_EXECUTOR,
        _delete_model_provider_for_token,
        token,
        provider_value,
        authn.client_ip(request),
    )


def _revocation_state(begin_data: dict) -> tuple[bool, int | None]:
    already_absent = begin_data.get("already_absent") is True
    generation = begin_data.get("generation")
    if not already_absent and (not isinstance(generation, int) or isinstance(generation, bool) or generation < 1):
        raise ValueError("credential revocation returned invalid state")
    return already_absent, generation


def _delete_model_provider_for_token(token: str, provider: str, forwarded_for: str) -> JSONResponse:
    begin_status, begin_data = call(
        config.ACCOUNT_URL,
        "POST",
        "/v1/model-providers/revoke-begin",
        {"token": token, "provider": provider},
        extra={"X-Forwarded-For": forwarded_for},
        timeout=CONTROL_PLANE_TIMEOUT_SECONDS,
    )
    if begin_status != 200 or not isinstance(begin_data, dict):
        return JSONResponse(begin_data, status_code=begin_status)
    try:
        already_absent, generation = _revocation_state(begin_data)
    except ValueError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=502)
    if already_absent:
        log.info("model_provider_delete", provider=provider, status=200, already_absent=True)
        return JSONResponse(
            {
                "provider": provider,
                "generation": generation,
                "deleted": False,
                "already_absent": True,
            }
        )
    try:
        finalize_token = config.BRAIN_FINALIZE_TOKEN_FILE.read_text().strip()
    except OSError:
        finalize_token = ""
    if not finalize_token:
        log.warning("brain_finalize_unavailable", provider=provider)
        return JSONResponse(
            {"detail": "Brain credential finalization is unavailable"},
            status_code=502,
        )
    status, data = call(
        config.ACCOUNT_URL,
        "POST",
        "/v1/internal/model-providers/revoke-finalize",
        {"token": token, "provider": provider, "generation": generation},
        extra={
            "Authorization": f"Bearer {finalize_token}",
            "X-Forwarded-For": forwarded_for,
        },
        timeout=CONTROL_PLANE_TIMEOUT_SECONDS,
    )
    log.info("model_provider_delete", provider=provider, status=status)
    return JSONResponse(data, status_code=status)
