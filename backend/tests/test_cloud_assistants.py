import contextlib
import json
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar

from fastapi.testclient import TestClient

from app import authn, config, main

VERIFY_CAPABILITY = "a" * 64


class _AssistantControlHandler(BaseHTTPRequestHandler):
    calls: list[tuple[str, str, dict, str]]
    assistant_status = 200
    assistants: ClassVar[list[dict[str, object]]] = [
        {"assistant": "example-assistant", "status": "running"},
    ]

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self) -> None:
        self.calls.append(("GET", self.path, {}, self.headers.get("X-Shimpz-Account", "")))
        if self.path == "/v1/teams/team_one/assistants":
            self._json(
                self.assistant_status,
                {"assistants": self.assistants} if self.assistant_status == 200 else {"detail": "team unavailable"},
            )
            return
        self._json(404, {"detail": "not found"})

    def do_POST(self) -> None:
        body = self._body()
        token = self.headers.get("X-Shimpz-Account", "")
        self.calls.append(("POST", self.path, body, token))
        if self.path == "/v1/verify":
            if self.headers.get("Authorization") != f"Bearer {VERIFY_CAPABILITY}":
                self._json(403, {"detail": "invalid credentials"})
                return
            if body.get("token") == "valid-token":
                self._json(200, {"account_id": "account-1", "username": "account-user"})
            else:
                self._json(401, {"detail": "invalid token"})
            return
        if self.path == "/v1/teams/team_one/assistants":
            self._json(
                self.assistant_status,
                {"installed": True} if self.assistant_status == 200 else {"detail": "blocked"},
            )
            return
        self._json(404, {"detail": "not found"})

    def do_DELETE(self) -> None:
        self.calls.append(("DELETE", self.path, {}, self.headers.get("X-Shimpz-Account", "")))
        if self.path.startswith("/v1/teams/team_one/assistants/"):
            self._json(
                self.assistant_status if self.path.endswith("/example-assistant") else 404,
                {"uninstalled": True}
                if self.assistant_status == 200 and self.path.endswith("/example-assistant")
                else {"detail": "blocked"},
            )
            return
        self._json(404, {"detail": "not found"})

    def log_message(self, *_args) -> None:
        pass


@contextlib.contextmanager
def _assistant_control_plane(*, assistant_status: int = 200, assistants: list[dict] | None = None):
    calls: list[tuple[str, str, dict, str]] = []
    handler = type(
        "_ScopedAssistantControlHandler",
        (_AssistantControlHandler,),
        {
            "calls": calls,
            "assistant_status": assistant_status,
            "assistants": _AssistantControlHandler.assistants if assistants is None else assistants,
        },
    )
    with tempfile.TemporaryDirectory() as temporary:
        token_path = Path(temporary) / "account-verify"
        token_path.write_text(VERIFY_CAPABILITY, encoding="ascii")
        token_path.chmod(0o440)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        worker = threading.Thread(
            target=server.serve_forever,
            kwargs={"poll_interval": 0.01},
            daemon=True,
        )
        worker.start()
        previous = authn.ACCOUNT_URL, authn.ACCOUNT_VERIFY_TOKEN_FILE, config.TEAM_URL
        authn.ACCOUNT_URL = config.TEAM_URL = f"http://127.0.0.1:{server.server_port}"
        authn.ACCOUNT_VERIFY_TOKEN_FILE = token_path
        try:
            yield calls
        finally:
            authn.ACCOUNT_URL, authn.ACCOUNT_VERIFY_TOKEN_FILE, config.TEAM_URL = previous
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)


def _authenticate(client: TestClient) -> None:
    client.cookies.set(main.ACCOUNT_COOKIE, "valid-token")


def _mutation_headers() -> dict[str, str]:
    return {"Origin": "https://shimpz.com", "Content-Type": "application/json"}


def _assert_private(response) -> None:
    assert response.headers["cache-control"] == "private, no-store"


def test_cloud_assistant_lifecycle_requires_authentication_before_upstream():
    with _assistant_control_plane() as calls, TestClient(main.app) as client:
        responses = (
            client.get("/api/teams/team_one/assistants"),
            client.get("/api/teams/team_one/chat/assistants"),
            client.post(
                "/api/teams/team_one/assistants",
                content=b'{"assistant_id":"shimpz-cloudflare","source_digest":"sha256:' + b"a" * 64 + b'"}',
                headers=_mutation_headers(),
            ),
            client.delete(
                "/api/teams/team_one/assistants/shimpz-cloudflare",
                headers={"Origin": "https://shimpz.com"},
            ),
        )
    assert [response.status_code for response in responses] == [401, 401, 401, 401]
    assert calls == []
    for response in responses:
        assert response.json() == {"detail": "not authenticated"}
        _assert_private(response)


def test_cloud_assistant_inventory_projects_only_bound_ids_without_private_runtime_data():
    with _assistant_control_plane() as calls, TestClient(main.app) as client:
        _authenticate(client)
        response = client.get("/api/teams/team_one/assistants")
    assert response.status_code == 200
    assert response.json() == {"installed": ["example-assistant"]}
    _assert_private(response)
    assert ("GET", "/v1/teams/team_one/assistants", {}, "valid-token") in calls


def test_cloud_chat_scope_projects_only_running_assistants():
    with _assistant_control_plane() as calls, TestClient(main.app) as client:
        _authenticate(client)
        response = client.get("/api/teams/team_one/chat/assistants")
    assert response.status_code == 200
    assert response.json() == {"assistant_ids": ["example-assistant"]}
    _assert_private(response)
    assert ("GET", "/v1/teams/team_one/assistants", {}, "valid-token") in calls


def test_cloud_chat_scope_is_brain_only_when_the_assistant_is_not_running():
    assistants = [
        {"assistant": "example-assistant", "status": "stopped"},
    ]
    with _assistant_control_plane(assistants=assistants), TestClient(main.app) as client:
        _authenticate(client)
        response = client.get("/api/teams/team_one/chat/assistants")
    assert response.status_code == 200
    assert response.json() == {"assistant_ids": []}
    _assert_private(response)


def test_cloud_chat_scope_fails_closed_on_ambiguous_running_inventory():
    assistants = [
        {"assistant": "example-assistant", "status": "running"},
        {"assistant": "example-assistant", "status": "running"},
    ]
    with _assistant_control_plane(assistants=assistants), TestClient(main.app) as client:
        _authenticate(client)
        response = client.get("/api/teams/team_one/chat/assistants")
    assert response.status_code == 502
    assert response.json() == {"detail": "invalid chat Assistant inventory"}
    _assert_private(response)


def test_cloud_assistant_install_rejects_origin_content_type_and_shape_before_team():
    digest = b"sha256:" + b"a" * 64
    cases = (
        (
            "/api/teams/team_one/assistants",
            {},
            b'{"assistant_id":"shimpz-cloudflare","source_digest":"' + digest + b'"}',
            403,
        ),
        (
            "/api/teams/team_one/assistants",
            {"Origin": "https://store.shimpz.com", "Content-Type": "application/json"},
            b'{"assistant_id":"shimpz-cloudflare","source_digest":"' + digest + b'"}',
            403,
        ),
        (
            "/api/teams/team_one/assistants",
            {"Origin": "https://shimpz.com", "Content-Type": "text/plain"},
            b'{"assistant_id":"shimpz-cloudflare","source_digest":"' + digest + b'"}',
            415,
        ),
        (
            "/api/teams/team_one/assistants",
            _mutation_headers(),
            b'{"assistant_id":"shimpz-cloudflare","source_digest":"' + digest + b'","image":"attacker/image"}',
            400,
        ),
        (
            "/api/teams/team_one/assistants",
            _mutation_headers(),
            b'{"assistant_id":"unknown-assistant","source_digest":"sha256:bad"}',
            400,
        ),
        (
            "/api/teams/TEAM_ONE/assistants",
            _mutation_headers(),
            b'{"assistant_id":"shimpz-cloudflare","source_digest":"' + digest + b'"}',
            400,
        ),
    )
    with _assistant_control_plane() as calls, TestClient(main.app) as client:
        _authenticate(client)
        responses = [client.post(path, content=body, headers=headers) for path, headers, body, _ in cases]
    assert [response.status_code for response in responses] == [case[3] for case in cases]
    assert not any(path.endswith("/assistants") for _method, path, _body, _token in calls)
    for response in responses:
        _assert_private(response)


def test_retired_app_routes_and_field_are_absent():
    with _assistant_control_plane() as calls, TestClient(main.app) as client:
        _authenticate(client)
        old_install = client.post(
            "/api/teams/team_one/install",
            json={"app": "shimpz-cloudflare"},
            headers=_mutation_headers(),
        )
        old_list = client.get("/api/teams/team_one/apps")
        old_delete = client.delete(
            "/api/teams/team_one/apps/shimpz-cloudflare",
            headers={"Origin": "https://shimpz.com"},
        )
        retired_field = client.post(
            "/api/teams/team_one/assistants",
            json={"app": "shimpz-cloudflare"},
            headers=_mutation_headers(),
        )
    assert [old_install.status_code, old_list.status_code, old_delete.status_code] == [405, 404, 405]
    assert retired_field.status_code == 400
    assert retired_field.json() == {"detail": "body must contain only assistant_id and source_digest"}
    _assert_private(retired_field)
    assert [path for _method, path, _body, _token in calls] == ["/v1/verify"]


def test_cloud_assistant_delete_rejects_untrusted_origins_before_team():
    cases = (
        ("/api/teams/team_one/assistants/example-assistant", {}, 403),
        (
            "/api/teams/team_one/assistants/example-assistant",
            {"Origin": "https://shimpz.com.evil.example"},
            403,
        ),
        (
            "/api/teams/team_one/assistants/retired-assistant",
            {"Origin": "https://shimpz.com"},
            404,
        ),
        (
            "/api/teams/TEAM_ONE/assistants/example-assistant",
            {"Origin": "https://shimpz.com"},
            400,
        ),
    )
    with _assistant_control_plane() as calls, TestClient(main.app) as client:
        _authenticate(client)
        responses = [client.delete(path, headers=headers) for path, headers, _status in cases]
    assert [response.status_code for response in responses] == [case[2] for case in cases]
    assert [path for method, path, _body, _token in calls if method == "DELETE"] == [
        "/v1/teams/team_one/assistants/retired-assistant"
    ]
    for response in responses:
        _assert_private(response)


def test_cloud_assistant_mutations_translate_only_identity_and_refreshable_acceptance():
    source_digest = f"sha256:{'a' * 64}"
    with _assistant_control_plane() as calls, TestClient(main.app) as client:
        _authenticate(client)
        installed = client.post(
            "/api/teams/team_one/assistants",
            json={
                "assistant_id": "example-assistant",
                "source_digest": source_digest,
            },
            headers=_mutation_headers(),
        )
        removed = client.delete(
            "/api/teams/team_one/assistants/example-assistant",
            headers={"Origin": "https://shimpz.com"},
        )
        retired_removed = client.delete(
            "/api/teams/team_one/assistants/retired-assistant",
            headers={"Origin": "https://shimpz.com"},
        )
    assert installed.status_code == removed.status_code == 200
    assert retired_removed.status_code == 404
    assert installed.json() == {"assistant": "example-assistant", "accepted": True}
    assert removed.json() == {"assistant": "example-assistant", "accepted": True}
    for response in (installed, removed, retired_removed):
        _assert_private(response)
    assert (
        "POST",
        "/v1/teams/team_one/assistants",
        {
            "assistant_id": "example-assistant",
            "source_digest": source_digest,
        },
        "valid-token",
    ) in calls
    assert (
        "DELETE",
        "/v1/teams/team_one/assistants/example-assistant",
        {},
        "valid-token",
    ) in calls
    assert (
        "DELETE",
        "/v1/teams/team_one/assistants/retired-assistant",
        {},
        "valid-token",
    ) in calls


def test_cloud_assistant_upstream_failures_remain_private_and_typed():
    source_digest = f"sha256:{'a' * 64}"
    with _assistant_control_plane(assistant_status=503), TestClient(main.app) as client:
        _authenticate(client)
        inventory = client.get("/api/teams/team_one/assistants")
        install = client.post(
            "/api/teams/team_one/assistants",
            json={
                "assistant_id": "example-assistant",
                "source_digest": source_digest,
            },
            headers=_mutation_headers(),
        )
        uninstall = client.delete(
            "/api/teams/team_one/assistants/example-assistant",
            headers={"Origin": "https://shimpz.com"},
        )
    assert [response.status_code for response in (inventory, install, uninstall)] == [
        503,
        503,
        503,
    ]
    for response in (inventory, install, uninstall):
        _assert_private(response)
