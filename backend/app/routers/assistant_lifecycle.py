"""Authenticated Store-to-Team Assistant mutation boundary."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app import authn, config
from app.access import mutation_origin_allowed
from app.config import MAX_ASSISTANT_INSTALL_BODY_BYTES
from app.control import EXECUTOR as CONTROL_EXECUTOR
from app.payloads import ClientPayloadError, read_bounded_json
from app.protocol.http.v1 import payload as team_contract
from app.upstream import CONTROL_PLANE_TIMEOUT_SECONDS, call_bounded


@dataclass(frozen=True, slots=True)
class AssistantMutation:
    account_id: str
    team_id: str
    assistant_id: str
    status: int
    data: dict


def _canonical_ids(team_id: str, assistant_id: object) -> tuple[str, str]:
    canonical_team = team_contract.canonical_team_id(team_id)
    canonical_assistant = team_contract.canonical_assistant_id(assistant_id)
    if canonical_team is None:
        raise ClientPayloadError(400, "bad team id")
    if canonical_assistant is None:
        raise ClientPayloadError(400, "bad Assistant id")
    return canonical_team, canonical_assistant


async def install_assistant_publication(request: Request, team_id: str) -> AssistantMutation:
    token, account_id, _ = await authn.authed_account_bounded(request)
    if not token:
        raise ClientPayloadError(401, "not authenticated")
    if not mutation_origin_allowed(request.headers.get("origin")):
        raise ClientPayloadError(403, "forbidden origin")
    if request.headers.get("content-type", "").strip().lower() != "application/json":
        raise ClientPayloadError(415, "Content-Type must be application/json")
    payload = await read_bounded_json(request, MAX_ASSISTANT_INSTALL_BODY_BYTES)
    if set(payload) != {"assistant_id", "source_digest"}:
        raise ClientPayloadError(400, "body must contain only assistant_id and source_digest")
    canonical_team = team_contract.canonical_team_id(team_id)
    assistant_id = team_contract.canonical_assistant_id(payload["assistant_id"])
    source_digest = team_contract.canonical_source_digest(payload["source_digest"])
    if canonical_team is None:
        raise ClientPayloadError(400, "bad team id")
    if assistant_id is None:
        raise ClientPayloadError(400, "bad Assistant id")
    if source_digest is None:
        raise ClientPayloadError(400, "bad source digest")
    status, data = await call_bounded(
        CONTROL_EXECUTOR,
        config.TEAM_URL,
        "POST",
        f"/v1/teams/{canonical_team}/assistants",
        {"assistant_id": assistant_id, "source_digest": source_digest},
        {"X-Shimpz-Account": token},
        timeout=CONTROL_PLANE_TIMEOUT_SECONDS,
    )
    return AssistantMutation(account_id, canonical_team, assistant_id, status, data)


async def uninstall_assistant(
    request: Request,
    team_id: str,
    assistant_id: str,
) -> AssistantMutation:
    token, account_id, _ = await authn.authed_account_bounded(request)
    if not token:
        raise ClientPayloadError(401, "not authenticated")
    if not mutation_origin_allowed(request.headers.get("origin")):
        raise ClientPayloadError(403, "forbidden origin")
    canonical_team, canonical_assistant = _canonical_ids(team_id, assistant_id)
    status, data = await call_bounded(
        CONTROL_EXECUTOR,
        config.TEAM_URL,
        "DELETE",
        f"/v1/teams/{canonical_team}/assistants/{canonical_assistant}",
        extra={"X-Shimpz-Account": token},
        timeout=CONTROL_PLANE_TIMEOUT_SECONDS,
    )
    return AssistantMutation(account_id, canonical_team, canonical_assistant, status, data)
