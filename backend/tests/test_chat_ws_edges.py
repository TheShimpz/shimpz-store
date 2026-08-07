"""Failure and cleanup coverage for Hosted chat WebSocket orchestration."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import WebSocketDisconnect

from app.chat import ws
from app.payloads import ClientPayloadError


class _Socket:
    def __init__(self):
        self.json = []
        self.sent = []
        self.closed = []
        self.accepted = []

    async def send_json(self, value):
        self.json.append(value)

    async def send(self, value):
        self.sent.append(value)

    async def close(self, *, code):
        self.closed.append(code)

    async def accept(self, *, subprotocol):
        self.accepted.append(subprotocol)


class _Lease:
    def __init__(self):
        self.released = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def release(self):
        self.released += 1

    def cancel_if_queued(self):
        return False


def test_relay_abort_does_not_repeat_stop(monkeypatch):
    async def scenario():
        socket = _Socket()
        stopped = []

        async def stop(*_args):
            stopped.append(True)

        monkeypatch.setattr(ws, "_stop_delivery_once", stop)
        delivery = ws._RelayDelivery(aborted=True)
        turn = ws._WsTurn(socket, "team", {}, "", asyncio.Event(), asyncio.Event())
        await ws._send_relay_event(
            turn,
            {"type": "error", "status": 502, "detail": "failed", "_relay_abort": True},
            delivery,
        )
        assert stopped == []
        assert delivery.terminal_seen

    asyncio.run(scenario())


def test_team_stop_translates_executor_saturation(monkeypatch):
    class Loop:
        def run_in_executor(self, *_args):
            raise ws._ExecutorSaturatedError("full")

    monkeypatch.setattr(ws.asyncio, "get_running_loop", lambda: Loop())
    assert asyncio.run(ws._team_stop("team", {})) == (429, {"detail": "chat stop capacity reached"})


def test_capacity_event_is_closed():
    assert ws._relay_capacity_event() == {
        "type": "error",
        "status": 429,
        "detail": "chat relay capacity reached",
    }


def test_admitted_turn_translates_executor_saturation(monkeypatch):
    class Loop:
        def run_in_executor(self, *_args):
            raise ws._ExecutorSaturatedError("full")

    async def scenario():
        socket = _Socket()
        started = asyncio.Event()
        turn = ws._WsTurn(socket, "team", {}, "hello", started, asyncio.Event())
        monkeypatch.setattr(ws.asyncio, "get_running_loop", lambda: Loop())
        await ws._ws_run_admitted_turn(turn, _Lease())
        assert started.is_set()
        assert socket.json == [ws._relay_capacity_event()]

    asyncio.run(scenario())


def test_turn_without_admission_reports_capacity(monkeypatch):
    monkeypatch.setattr(ws._TURN_ADMISSION, "reserve", lambda: None)

    async def scenario():
        socket = _Socket()
        started = asyncio.Event()
        await ws._ws_run_turn(
            socket,
            "team",
            {},
            {"message": "hello", "files": [], "assistant_ids": []},
            started,
        )
        assert started.is_set()
        assert socket.json == [ws._relay_capacity_event()]

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("status", "data", "expected_type"),
    [
        (503, {}, "error"),
        (200, {"status": "human-denied", "team_id": "other", "reason": "denied"}, "error"),
        (200, {"status": "human-denied", "team_id": "team", "reason": "other"}, "done"),
    ],
)
def test_resume_human_projects_upstream_failures(monkeypatch, status, data, expected_type):
    monkeypatch.setattr(ws, "_call", lambda *_args, **_kwargs: (status, data))

    async def scenario():
        started = asyncio.Event()
        result = ws._resume_human("team", {}, {}, asyncio.get_running_loop(), started)
        await asyncio.sleep(0)
        assert started.is_set()
        assert result["type"] == expected_type

    asyncio.run(scenario())


def test_start_human_constructs_and_returns_a_tracked_turn(monkeypatch):
    async def run(_turn, _lease):
        return None

    monkeypatch.setattr(ws, "_ws_run_admitted_turn", run)

    async def scenario():
        socket = _Socket()
        state = {}
        task, started, dispatched, delivery = ws._start_ws_human(
            ws._WsContext(socket, "team", {}, state),
            {"challenge_id": "a" * 32, "decision": "deny"},
            _Lease(),
        )
        await task
        assert not started.is_set() and not dispatched.is_set()
        assert isinstance(delivery, ws._RelayDelivery)

    asyncio.run(scenario())


def test_stop_turn_handles_already_stopped_and_failed_stop(monkeypatch):
    async def scenario():
        socket = _Socket()
        state = {"stop_requested": True}
        await ws._ws_stop_turn(socket, "team", {}, state)
        assert socket.json == []

        task = asyncio.create_task(asyncio.sleep(10))
        started = asyncio.Event()
        dispatched = asyncio.Event()
        started.set()
        dispatched.set()
        active = ws._ActiveTurn(task, started, dispatched, _Lease(), ws._RelayDelivery())
        state = {"active": active, "stop_requested": False}

        async def failed(*_args):
            return 503, {"requested": False}

        monkeypatch.setattr(ws, "_stop_delivery_once", failed)
        await ws._ws_stop_turn(socket, "team", {}, state)
        assert socket.json[-1]["status"] == 503
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

        task = asyncio.create_task(asyncio.sleep(10))
        active = ws._ActiveTurn(task, started, dispatched, _Lease(), ws._RelayDelivery())
        state = {"active": active, "stop_requested": False}

        async def already_attempted(*_args):
            return None

        monkeypatch.setattr(ws, "_stop_delivery_once", already_attempted)
        previous = list(socket.json)
        await ws._ws_stop_turn(socket, "team", {}, state)
        assert socket.json == previous
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    asyncio.run(scenario())


def test_tracked_turn_callback_preserves_a_newer_active_turn():
    async def scenario():
        lease = _Lease()
        task = asyncio.create_task(asyncio.sleep(0))
        state = {}
        ws._track_ws_turn(state, (task, asyncio.Event(), asyncio.Event(), ws._RelayDelivery()), lease)
        newer = object()
        state["active"] = newer
        await task
        await asyncio.sleep(0)
        assert state["active"] is newer
        assert lease.released == 1

    asyncio.run(scenario())


def test_human_response_rejects_active_pending_payload_and_capacity(monkeypatch):
    async def scenario():
        socket = _Socket()
        active_task = asyncio.create_task(asyncio.sleep(10))
        active = SimpleNamespace(task=active_task)
        await ws._ws_human_response(socket, "team", {}, {}, {"active": active})
        assert socket.json[-1]["status"] == 409
        active_task.cancel()
        await asyncio.gather(active_task, return_exceptions=True)

        await ws._ws_human_response(socket, "team", {}, {}, {"active": None, "pending_human": None})
        assert socket.json[-1]["status"] == 409

        pending = {"challenge_id": "a" * 32, "request": {"kind": "approval"}}
        invalid = {"type": "human-response", "challenge_id": "a" * 32, "decision": "bad"}
        await ws._ws_human_response(
            socket, "team", {}, invalid, {"active": None, "pending_human": pending}
        )
        assert socket.json[-1]["status"] == 400

        valid = {"type": "human-response", "challenge_id": "a" * 32, "decision": "deny"}
        monkeypatch.setattr(ws._TURN_ADMISSION, "reserve", lambda: None)
        await ws._ws_human_response(
            socket, "team", {}, valid, {"active": None, "pending_human": pending}
        )
        assert socket.json[-1] == ws._relay_capacity_event()

    asyncio.run(scenario())


def test_human_response_and_chat_dispatch_release_lease_when_start_fails(monkeypatch):
    def fail(*_args):
        raise RuntimeError("failed")

    async def scenario():
        socket = _Socket()
        human_lease = _Lease()
        monkeypatch.setattr(ws._TURN_ADMISSION, "reserve", lambda: human_lease)
        monkeypatch.setattr(ws, "_start_ws_human", fail)
        pending = {"challenge_id": "a" * 32, "request": {"kind": "approval"}}
        message = {"type": "human-response", "challenge_id": "a" * 32, "decision": "deny"}
        with pytest.raises(RuntimeError):
            await ws._ws_human_response(
                socket, "team", {}, message, {"active": None, "pending_human": pending}
            )
        assert human_lease.released == 1

        chat_lease = _Lease()
        monkeypatch.setattr(ws._TURN_ADMISSION, "reserve", lambda: chat_lease)
        monkeypatch.setattr(ws, "_start_ws_turn", fail)
        chat = {"type": "chat", "message": "hello", "files": [], "assistant_ids": []}
        with pytest.raises(RuntimeError):
            await ws._ws_dispatch(socket, "team", {}, chat, {"active": None, "pending_human": None})
        assert chat_lease.released == 1

    asyncio.run(scenario())


def test_chat_dispatch_translates_shape_and_payload_errors(monkeypatch):
    async def scenario():
        socket = _Socket()
        state = {"active": None, "pending_human": None}
        await ws._ws_dispatch(socket, "team", {}, {"type": "chat"}, state)
        assert socket.json[-1]["status"] == 400

        def invalid(_payload):
            raise ClientPayloadError(413, "too large")

        monkeypatch.setattr(ws, "_chat_turn_payload", invalid)
        message = {"type": "chat", "message": "hello", "files": [], "assistant_ids": []}
        await ws._ws_dispatch(socket, "team", {}, message, state)
        assert socket.json[-1] == {"type": "error", "status": 413, "detail": "too large"}

    asyncio.run(scenario())


def test_identity_translates_auth_executor_saturation(monkeypatch):
    async def fail(_socket):
        raise ws._ExecutorSaturatedError("full")

    monkeypatch.setattr(ws, "_ws_verify", fail)

    async def scenario():
        socket = _Socket()
        assert await ws._ws_identity(socket, "team") is None
        assert socket.closed == [4429]

    asyncio.run(scenario())


def test_websocket_capacity_returns_http_rejection(monkeypatch):
    monkeypatch.setattr(ws, "_ws_validate_opening", lambda _socket: _async_value(True))
    monkeypatch.setattr(ws, "_ws_identity", lambda _socket, _team: _async_value(("token", "account", "team")))
    monkeypatch.setattr(ws._WS_CONNECTION_ADMISSION, "reserve", lambda *_args: None)

    async def scenario():
        socket = _Socket()
        await ws.team_chat_ws(socket, "team")
        assert [message["type"] for message in socket.sent] == [
            "websocket.http.response.start",
            "websocket.http.response.body",
        ]

    asyncio.run(scenario())


async def _async_value(value):
    return value


def test_websocket_disconnect_cleans_active_and_pending_work(monkeypatch):
    class Connection:
        def __init__(self):
            self.released = False

        def release(self):
            self.released = True

    async def run_case(*, pending):
        connection = Connection()
        monkeypatch.setattr(ws, "_ws_validate_opening", lambda _socket: _async_value(True))
        monkeypatch.setattr(
            ws, "_ws_identity", lambda _socket, _team: _async_value(("token", "account", "team"))
        )
        monkeypatch.setattr(ws._WS_CONNECTION_ADMISSION, "reserve", lambda *_args: connection)
        receives = 0

        async def receive(_socket):
            nonlocal receives
            receives += 1
            if receives == 1:
                return {"type": "test"}
            raise WebSocketDisconnect

        monkeypatch.setattr(ws, "_ws_receive_bounded_json", receive)
        task_holder = []

        async def dispatch(_socket, _team, _headers, _message, state):
            if pending:
                state["pending_human"] = {"challenge_id": "a" * 32}
            else:
                task = asyncio.create_task(asyncio.sleep(10))
                task_holder.append(task)
                state["active"] = SimpleNamespace(task=task)

        monkeypatch.setattr(ws, "_ws_dispatch", dispatch)
        stopped = []

        async def stop(*_args):
            stopped.append(True)
            return 200, {}

        monkeypatch.setattr(ws, "_team_stop", stop)
        await ws.team_chat_ws(_Socket(), "team")
        assert connection.released
        if pending:
            assert stopped == [True]
        else:
            assert task_holder[0].cancelled()

    asyncio.run(run_case(pending=False))
    asyncio.run(run_case(pending=True))
