"""Core Team identity and lifecycle routes."""

from __future__ import annotations

import hashlib
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import authn, config
from app.access import private_json, require_json_mutation
from app.config import MAX_TEAM_CREATE_BODY_BYTES
from app.control import EXECUTOR as CONTROL_EXECUTOR
from app.inference import model as canonical_model
from app.inference import provider as canonical_provider
from app.payloads import ClientPayloadError, read_bounded_json
from app.protocol.http.v1 import payload as team_contract
from app.upstream import CONTROL_PLANE_TIMEOUT_SECONDS, call_bounded

router = APIRouter()


def team_id_for(account_id: str, team_name: str) -> str:
    """Derive a Docker/PG-safe ID that binds the complete Account identity and the exact validated Team name.

    The lossy slug only admits a name and keeps a bounded readable suffix; it never decides identity, so names whose
    slugs agree remain distinct Teams.
    """
    slug = re.sub(r"[^a-z0-9_]+", "_", team_name.lower()).strip("_")
    try:
        digest = hashlib.sha256(f"{account_id}\0{team_name}".encode()).hexdigest()[:24]
    except UnicodeEncodeError:
        return ""
    return f"{digest}_{slug[:15]}".rstrip("_") if slug else ""


def _create_payload(payload: dict, account_id: str) -> tuple[str, dict[str, str]]:
    if set(payload) != {"team_name", "provider", "model"}:
        raise ClientPayloadError(400, "Team requires team_name, provider, and model")
    raw_name = payload["team_name"]
    team_name = team_contract.canonical_team_name(raw_name.strip() if isinstance(raw_name, str) else None)
    provider = canonical_provider(payload.get("provider"))
    model = canonical_model(provider, payload.get("model")) if provider is not None else None
    team_id = team_id_for(account_id, team_name) if team_name is not None else ""
    if not team_id:
        raise ClientPayloadError(400, "bad team name")
    if provider is None:
        raise ClientPayloadError(400, "unsupported model provider")
    if model is None:
        raise ClientPayloadError(400, "unsupported model for provider")
    return team_id, {"team_name": team_name, "provider": provider, "model": model}


@router.get("/api/teams")
async def teams_list(request: Request) -> JSONResponse:
    token, _, _ = await authn.authed_account_bounded(request)
    if not token:
        return private_json({"detail": "not authenticated"}, 401)
    status, data = await call_bounded(
        CONTROL_EXECUTOR,
        config.TEAM_URL,
        "GET",
        "/v1/teams",
        extra={team_contract.ACCOUNT_SESSION_HEADER: token},
        timeout=CONTROL_PLANE_TIMEOUT_SECONDS,
    )
    return private_json(data, status)


@router.post("/api/teams")
async def teams_create(request: Request) -> JSONResponse:
    token, account_id, _ = await authn.authed_account_bounded(request)
    if not token:
        return private_json({"detail": "not authenticated"}, 401)
    require_json_mutation(request)
    payload = await read_bounded_json(request, MAX_TEAM_CREATE_BODY_BYTES)
    team_id, create_payload = _create_payload(payload, account_id)
    status, data = await call_bounded(
        CONTROL_EXECUTOR,
        config.TEAM_URL,
        "POST",
        f"/v1/teams/{team_id}/create",
        create_payload,
        {team_contract.ACCOUNT_SESSION_HEADER: token},
        timeout=CONTROL_PLANE_TIMEOUT_SECONDS,
    )
    return private_json(data, status)


@router.delete("/api/teams/{team_id}")
async def teams_destroy(request: Request, team_id: str) -> JSONResponse:
    token, _, _ = await authn.authed_account_bounded(request)
    if not token:
        return private_json({"detail": "not authenticated"}, 401)
    team_id = team_contract.canonical_team_id(team_id)
    if team_id is None:
        return private_json({"detail": "bad team id"}, 400)
    status, data = await call_bounded(
        CONTROL_EXECUTOR,
        config.TEAM_URL,
        "DELETE",
        f"/v1/teams/{team_id}",
        extra={team_contract.ACCOUNT_SESSION_HEADER: token},
        timeout=CONTROL_PLANE_TIMEOUT_SECONDS,
    )
    return private_json(data, status)
