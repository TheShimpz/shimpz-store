"""Every authenticated Team, model-provider, and inference response is private and never stored."""

from fastapi.testclient import TestClient

from app import authn
from app.main import app
from app.routers import inference, model_providers, teams
from tests.request_fixture import session

ORIGIN = {"Origin": "https://shimpz.com"}
CREDENTIAL = {"auth_type": "api_key", "secret": "sk-browser-contract-key"}
TEAM = {"team_name": "Astra", "provider": "openai", "model": "gpt-6-luna"}
SELECTION = {"provider": "openai", "model": "gpt-6-luna", "effort": "low"}


def _requests(client):
    return (
        client.get("/api/teams"),
        client.post("/api/teams", json=TEAM, headers=ORIGIN),
        client.delete("/api/teams/team"),
        client.get("/api/model-providers"),
        client.post("/api/model-providers/openai", json=CREDENTIAL, headers=ORIGIN),
        client.get("/api/teams/team/inference"),
        client.put("/api/teams/team/inference", json=SELECTION),
    )


def test_authenticated_team_credential_and_inference_responses_are_never_stored(monkeypatch):
    status = 200

    async def upstream(*_args, **_kwargs):
        return status, {"providers": [], "detail": "upstream"} if status == 200 else {"detail": "unavailable"}

    for module in (teams, model_providers, inference):
        monkeypatch.setattr(module, "call_bounded", upstream)
    monkeypatch.setattr(model_providers, "call", lambda *_args, **_kwargs: (503, {"detail": "unavailable"}))
    with TestClient(app) as client:
        monkeypatch.setattr(authn, "authed_account_bounded", session(True))
        succeeded = _requests(client)
        status = 503
        failed = (*_requests(client), client.delete("/api/model-providers/openai"))
        monkeypatch.setattr(authn, "authed_account_bounded", session(False))
        anonymous = _requests(client)
    for response in (*succeeded, *failed, *anonymous):
        assert response.headers.get("cache-control") == "private, no-store", response.request.url
