"""Released cloud Assistant lifecycle routes."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import authn, config
from app.access import private_json
from app.control import EXECUTOR as CONTROL_EXECUTOR
from app.projections import assistant_inventory, running_assistant_inventory
from app.protocol.http.v1 import payload as team_contract
from app.routers import assistant_lifecycle
from app.upstream import CONTROL_PLANE_TIMEOUT_SECONDS, call_bounded

log = structlog.get_logger()
router = APIRouter()


async def _assistant_inventory(
    request: Request,
    team_id: str,
    projector,
    response_key: str,
    invalid_detail: str,
    invalid_event: str,
) -> JSONResponse:
    token, _, _ = await authn.authed_account_bounded(request)
    if not token:
        return private_json({"detail": "not authenticated"}, 401)
    team_id = team_contract.canonical_team_id(team_id)
    if team_id is None:
        return private_json({"detail": "bad team id"}, 400)
    status, data = await call_bounded(
        CONTROL_EXECUTOR,
        config.TEAM_URL,
        "GET",
        f"/v1/teams/{team_id}/assistants",
        extra={team_contract.ACCOUNT_SESSION_HEADER: token},
        timeout=CONTROL_PLANE_TIMEOUT_SECONDS,
    )
    if status != 200:
        return private_json(data, status)
    projected = projector(data)
    if projected is None:
        log.warning(invalid_event, team_id=team_id)
        return private_json({"detail": invalid_detail}, 502)
    return private_json({response_key: projected})


@router.get("/api/teams/{team_id}/assistants")
async def cloud_assistants_list(request: Request, team_id: str) -> JSONResponse:
    return await _assistant_inventory(
        request,
        team_id,
        assistant_inventory,
        "installed",
        "invalid Assistant inventory",
        "assistant_inventory_invalid",
    )


@router.get("/api/teams/{team_id}/chat/assistants")
async def team_chat_assistants(request: Request, team_id: str) -> JSONResponse:
    """Return the verified default Assistant scope without exposing runtime metadata."""
    return await _assistant_inventory(
        request,
        team_id,
        running_assistant_inventory,
        "assistant_ids",
        "invalid chat Assistant inventory",
        "chat_assistant_inventory_invalid",
    )


@router.post("/api/teams/{team_id}/assistants")
async def cloud_assistant_install(request: Request, team_id: str) -> JSONResponse:
    result = await assistant_lifecycle.install_assistant_publication(request, team_id)
    log.info(
        "assistant_install",
        account=result.account_id,
        team_id=result.team_id,
        assistant=result.assistant_id,
        status=result.status,
    )
    if not 200 <= result.status < 300:
        return private_json(result.data, result.status)
    return private_json({"assistant": result.assistant_id, "accepted": True})


@router.delete("/api/teams/{team_id}/assistants/{assistant}")
async def cloud_assistant_uninstall(request: Request, team_id: str, assistant: str) -> JSONResponse:
    result = await assistant_lifecycle.uninstall_assistant(
        request,
        team_id,
        assistant,
    )
    log.info(
        "assistant_uninstall",
        account=result.account_id,
        team_id=result.team_id,
        assistant=result.assistant_id,
        status=result.status,
    )
    if not 200 <= result.status < 300:
        return private_json(result.data, result.status)
    return private_json({"assistant": result.assistant_id, "accepted": True})
