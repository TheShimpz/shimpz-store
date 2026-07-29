"""Closed browser-safe projections for Store controller responses."""

from __future__ import annotations

from app import team_contract
from app.config import MAX_CHAT_ASSISTANTS


def public_file_metadata(value: object) -> dict | None:
    """Copy only opaque, non-path file metadata from the trusted controller response."""
    return team_contract.project_file_metadata(value, include_usage=False)


def public_file_upload(value: object, expected_team_id: str) -> dict | None:
    return team_contract.project_storage_response(
        value,
        kind="upload",
        expected_team_id=expected_team_id,
        include_team_id=False,
    )


def public_file_inventory(value: object, expected_team_id: str) -> dict | None:
    return team_contract.project_storage_response(
        value,
        kind="list",
        expected_team_id=expected_team_id,
        include_team_id=False,
    )


def public_file_deletion(value: object, expected_team_id: str, expected_id: str) -> dict | None:
    return team_contract.project_storage_response(
        value,
        kind="delete",
        expected_team_id=expected_team_id,
        expected_file_id=expected_id,
        include_team_id=False,
    )


def assistant_inventory(data: object) -> list[str] | None:
    if not isinstance(data, dict) or set(data) != {"assistants"} or not isinstance(data["assistants"], list):
        return None
    installed: list[str] = []
    for item in data["assistants"]:
        if not isinstance(item, dict) or set(item) != {"assistant", "status"}:
            return None
        assistant = team_contract.canonical_assistant_id(item["assistant"])
        if assistant is None or assistant in installed or not isinstance(item["status"], str):
            return None
        installed.append(assistant)
    return installed


def running_assistant_inventory(data: object) -> list[str] | None:
    """Project only verified, runnable Assistants onto the browser chat scope."""
    if not isinstance(data, dict) or set(data) != {"assistants"} or not isinstance(data["assistants"], list):
        return None
    running: list[str] = []
    seen: set[str] = set()
    for item in data["assistants"]:
        if not isinstance(item, dict) or set(item) != {"assistant", "status"}:
            return None
        assistant = team_contract.canonical_assistant_id(item["assistant"])
        if assistant is None or assistant in seen:
            return None
        seen.add(assistant)
        status = item.get("status")
        if not isinstance(status, str):
            return None
        if status != "running":
            continue
        if len(running) >= MAX_CHAT_ASSISTANTS:
            return None
        running.append(assistant)
    return running
