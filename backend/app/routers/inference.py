"""Team model-selection routes."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import authn, config
from app.access import private_json
from app.config import MAX_INFERENCE_BODY_BYTES
from app.control import EXECUTOR as CONTROL_EXECUTOR
from app.inference import model as canonical_model
from app.inference import provider as canonical_provider
from app.payloads import read_bounded_json
from app.protocol.http.v1 import payload as team_contract
from app.upstream import CONTROL_PLANE_TIMEOUT_SECONDS, call_bounded

router = APIRouter()
# The closed chat reasoning efforts Team accepts for a Team's configuration (ADR-0074).
INFERENCE_EFFORTS = ("low", "medium", "high")


@router.get("/api/teams/{team_id}/inference")
async def team_inference(request: Request, team_id: str) -> JSONResponse:
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
        f"/v1/teams/{team_id}/inference",
        extra={team_contract.ACCOUNT_SESSION_HEADER: token},
        timeout=CONTROL_PLANE_TIMEOUT_SECONDS,
    )
    return private_json(data, status)


def _inference_selection(payload: object) -> tuple[dict[str, str] | None, str | None]:
    """Canonicalize one exact provider, model, and effort selection before forwarding it."""
    if not isinstance(payload, dict) or set(payload) != {"provider", "model", "effort"}:
        return None, "inference requires provider, model, and effort"
    if payload["effort"] not in INFERENCE_EFFORTS:
        return None, "unsupported reasoning effort"
    provider = canonical_provider(payload["provider"])
    if provider is None:
        return None, "unsupported model provider"
    model = canonical_model(provider, payload["model"])
    if model is None:
        return None, "unsupported model for provider"
    return {"provider": provider, "model": model, "effort": payload["effort"]}, None


@router.put("/api/teams/{team_id}/inference")
async def team_inference_configure(request: Request, team_id: str) -> JSONResponse:
    token, _, _ = await authn.authed_account_bounded(request)
    if not token:
        return private_json({"detail": "not authenticated"}, 401)
    team_id = team_contract.canonical_team_id(team_id)
    if team_id is None:
        return private_json({"detail": "bad team id"}, 400)
    selection, problem = _inference_selection(await read_bounded_json(request, MAX_INFERENCE_BODY_BYTES))
    if problem is not None:
        return private_json({"detail": problem}, 400)
    status, data = await call_bounded(
        CONTROL_EXECUTOR,
        config.TEAM_URL,
        "PUT",
        f"/v1/teams/{team_id}/inference",
        selection,
        extra={team_contract.ACCOUNT_SESSION_HEADER: token},
        timeout=CONTROL_PLANE_TIMEOUT_SECONDS,
    )
    return private_json(data, status)
