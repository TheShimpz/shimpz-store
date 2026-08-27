"""Authenticated shimpz.chat.v7 WebSocket admission, dispatch, and delivery."""

from __future__ import annotations

import asyncio
import contextlib
import functools
from dataclasses import dataclass, field

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app import authn, config
from app.chat.events import WebSocketPayloadError
from app.chat.events import chat_turn_payload as _chat_turn_payload
from app.chat.events import upstream_error_event as _upstream_error_event
from app.chat.events import validated_terminal_event as _validated_terminal_event
from app.chat.events import ws_receive_bounded_json as _ws_receive_bounded_json
from app.chat.relay import CHAT_TURN_TIMEOUT_SECONDS, _stream_lines, _StreamRelay
from app.concurrency import BoundedThreadPoolExecutor as _BoundedThreadPoolExecutor
from app.concurrency import ExecutorSaturatedError as _ExecutorSaturatedError
from app.concurrency import TurnAdmission as _TurnAdmission
from app.concurrency import TurnLease as _TurnLease
from app.concurrency import WsConnectionAdmission as _WsConnectionAdmission
from app.config import (
    ACCOUNT_COOKIE,
    CHAT_WS_SUBPROTOCOL,
    STOP_QUEUE_MAX,
    STOP_WORKER_THREADS,
    STREAM_TURN_QUEUE_MAX,
    STREAM_WORKER_THREADS,
    TERMINAL_CONTRACT_ERROR,
    WS_ACCOUNT_CONNECTION_LIMIT,
    WS_ALLOWED_ORIGINS,
    WS_GLOBAL_CONNECTION_LIMIT,
    WS_TEAM_CONNECTION_LIMIT,
)
from app.payloads import ClientPayloadError
from app.protocol.http.v1 import payload as team_contract
from app.protocol.http.v1 import websocket as chat_ws_contract
from app.upstream import CHAT_STOP_TIMEOUT_SECONDS, VERIFY_TIMEOUT_SECONDS
from app.upstream import call as _call
from app.upstream import call_bounded as _bounded_call

log = structlog.get_logger()

_STREAM_EXECUTOR = _BoundedThreadPoolExecutor(
    max_workers=STREAM_WORKER_THREADS,
    max_outstanding=STREAM_WORKER_THREADS,
    thread_name_prefix="shimpz-stream",
)
_TURN_ADMISSION = _TurnAdmission(STREAM_WORKER_THREADS, STREAM_TURN_QUEUE_MAX)
_STOP_EXECUTOR = _BoundedThreadPoolExecutor(
    max_workers=STOP_WORKER_THREADS,
    max_outstanding=STOP_WORKER_THREADS + STOP_QUEUE_MAX,
    thread_name_prefix="shimpz-stop",
)
_WS_CONNECTION_ADMISSION = _WsConnectionAdmission(
    WS_GLOBAL_CONNECTION_LIMIT,
    WS_ACCOUNT_CONNECTION_LIMIT,
    WS_TEAM_CONNECTION_LIMIT,
)
_AUTH_EXECUTOR = authn.EXECUTOR
_HUMAN_AUTH_KINDS = frozenset(
    {
        "auth:password",
        "auth:totp",
        "auth:passkey",
    }
)


async def _ws_verify(ws: WebSocket) -> tuple[str, str]:
    token = ws.cookies.get(ACCOUNT_COOKIE, "")
    if not token:
        return "", ""
    capability = authn.verification_capability()
    if not capability:
        return "", ""
    status, data = await _bounded_call(
        _AUTH_EXECUTOR,
        config.ACCOUNT_URL,
        "POST",
        "/v1/verify",
        {"token": token},
        extra={"Authorization": f"Bearer {capability}"},
        timeout=VERIFY_TIMEOUT_SECONDS,
    )
    account_id = data.get("account_id") if status == 200 else None
    return (token, str(account_id)) if account_id else ("", "")


@dataclass
class _RelayDelivery:
    terminal_seen: bool = False
    aborted: bool = False
    stop_attempted: bool = False


async def _stop_delivery_once(
    team_id: str,
    hdr: dict,
    delivery: _RelayDelivery,
) -> tuple[int, dict] | None:
    """Request provider cancellation at most once for one admitted relay."""
    if delivery.stop_attempted:
        return None
    delivery.stop_attempted = True
    return await _team_stop(team_id, hdr)


async def _send_relay_event(
    turn: _WsTurn,
    event: dict,
    delivery: _RelayDelivery,
) -> None:
    projected = dict(event)
    relay_abort = bool(projected.pop("_relay_abort", False))
    terminal = _validated_terminal_event(projected, turn.team_id)
    if terminal is None:
        terminal = {"type": "error", "status": 502, "detail": TERMINAL_CONTRACT_ERROR}
        relay_abort = True
    if relay_abort:
        if not delivery.aborted:
            await _stop_delivery_once(turn.team_id, turn.headers, delivery)
        delivery.aborted = True
    delivery.terminal_seen = True
    await turn.ws.send_json(terminal)
    if turn.state is not None:
        turn.state["pending_human"] = (
            {
                "challenge_id": terminal["challenge_id"],
                "request": terminal["request"],
            }
            if terminal["type"] == "human-required"
            else None
        )


async def _team_stop(team_id: str, hdr: dict) -> tuple[int, dict]:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(
            _STOP_EXECUTOR,
            functools.partial(
                _call,
                config.TEAM_URL,
                "POST",
                f"/v1/teams/{team_id}/chat/stop",
                None,
                hdr,
                timeout=CHAT_STOP_TIMEOUT_SECONDS,
            ),
        )
    except _ExecutorSaturatedError:
        return 429, {"detail": "chat stop capacity reached"}


@dataclass(frozen=True)
class _WsTurn:
    ws: WebSocket
    team_id: str
    headers: dict
    text: str
    started: asyncio.Event
    dispatched: asyncio.Event
    files: tuple[str, ...] = ()
    assistant_ids: tuple[str, ...] = ()
    delivery: _RelayDelivery = field(default_factory=_RelayDelivery)
    human_response: dict[str, object] | None = None
    state: dict | None = None


@dataclass(frozen=True)
class _WsContext:
    ws: WebSocket
    team_id: str
    headers: dict
    state: dict


@dataclass(frozen=True)
class _ActiveTurn:
    task: asyncio.Task
    started: asyncio.Event
    dispatched: asyncio.Event
    lease: _TurnLease
    delivery: _RelayDelivery


def _relay_capacity_event() -> dict:
    return {
        "type": "error",
        "status": 429,
        "detail": "chat relay capacity reached",
    }


async def _deliver_turn(turn: _WsTurn, worker: asyncio.Future) -> None:
    delivery = turn.delivery
    try:
        event = await asyncio.shield(worker)
        await _send_relay_event(turn, event, delivery)
    except WebSocketDisconnect, OSError, RuntimeError, asyncio.CancelledError:
        await _stop_delivery_once(turn.team_id, turn.headers, delivery)
        raise
    finally:
        with contextlib.suppress(asyncio.CancelledError, TimeoutError):
            await asyncio.wait_for(asyncio.shield(worker), timeout=15)


async def _ws_run_admitted_turn(turn: _WsTurn, lease: _TurnLease) -> None:
    async with lease:
        loop = asyncio.get_running_loop()
        try:
            operation = (
                functools.partial(
                    _resume_human,
                    turn.team_id,
                    turn.headers,
                    turn.human_response,
                    loop,
                    turn.started,
                )
                if turn.human_response is not None
                else functools.partial(
                    _stream_lines,
                    _StreamRelay(
                        turn.team_id,
                        turn.text,
                        turn.headers,
                        loop,
                        turn.started,
                        turn.files,
                        turn.assistant_ids,
                    ),
                )
            )
            worker = loop.run_in_executor(_STREAM_EXECUTOR, operation)
            turn.dispatched.set()
        except _ExecutorSaturatedError:
            turn.started.set()
            await turn.ws.send_json(_relay_capacity_event())
            return
        await _deliver_turn(turn, worker)


async def _ws_run_turn(
    ws: WebSocket,
    team_id: str,
    hdr: dict,
    payload: dict[str, object],
    started: asyncio.Event,
) -> None:
    """Relay one terminal controller event for a live turn."""
    admitted = _TURN_ADMISSION.reserve()
    if admitted is None:
        started.set()
        await ws.send_json(_relay_capacity_event())
        return
    dispatched = asyncio.Event()
    await _ws_run_admitted_turn(
        _WsTurn(
            ws=ws,
            team_id=team_id,
            headers=hdr,
            text=payload["message"],
            started=started,
            dispatched=dispatched,
            files=tuple(payload["files"]),
            assistant_ids=tuple(payload["assistant_ids"]),
        ),
        admitted,
    )


def _start_ws_turn(
    context: _WsContext,
    msg: dict,
    lease: _TurnLease,
) -> tuple[asyncio.Task, asyncio.Event, asyncio.Event, _RelayDelivery]:
    started = asyncio.Event()
    dispatched = asyncio.Event()
    delivery = _RelayDelivery()
    turn = asyncio.create_task(
        _ws_run_admitted_turn(
            _WsTurn(
                ws=context.ws,
                team_id=context.team_id,
                headers=context.headers,
                text=msg["message"],
                started=started,
                dispatched=dispatched,
                files=tuple(msg["files"]),
                assistant_ids=tuple(msg["assistant_ids"]),
                delivery=delivery,
                state=context.state,
            ),
            lease,
        )
    )
    return turn, started, dispatched, delivery


def _resume_human(
    team_id: str,
    headers: dict,
    response: dict[str, object],
    loop: asyncio.AbstractEventLoop,
    started: asyncio.Event,
) -> dict:
    """BLOCKING (run in a thread): resume one exact Hosted human challenge."""
    loop.call_soon_threadsafe(started.set)
    status, data = _call(
        config.TEAM_URL,
        "POST",
        f"/v1/teams/{team_id}/chat/human",
        response,
        headers,
        timeout=CHAT_TURN_TIMEOUT_SECONDS,
    )
    if status == 428 and isinstance(data, dict) and data.get("status") == "human-required":
        return {"type": "human-required", **data}
    if status != 200 or not isinstance(data, dict):
        return _upstream_error_event(status)
    if data.get("status") == "human-denied":
        expected = {"team_id", "status", "reason"}
        if set(data) != expected or data.get("team_id") != team_id:
            return {
                "type": "error",
                "status": 502,
                "detail": TERMINAL_CONTRACT_ERROR,
                "_relay_abort": True,
            }
        if data.get("reason") == "denied":
            return {"type": "stopped"}
        if data.get("reason") == "authentication-failed":
            return {
                "type": "error",
                "status": 403,
                "detail": "authentication was not confirmed",
            }
    return {"type": "done", **data}


def _start_ws_human(
    context: _WsContext,
    response: dict[str, object],
    lease: _TurnLease,
) -> tuple[asyncio.Task, asyncio.Event, asyncio.Event, _RelayDelivery]:
    started = asyncio.Event()
    dispatched = asyncio.Event()
    delivery = _RelayDelivery()
    turn = asyncio.create_task(
        _ws_run_admitted_turn(
            _WsTurn(
                ws=context.ws,
                team_id=context.team_id,
                headers=context.headers,
                text="",
                started=started,
                dispatched=dispatched,
                delivery=delivery,
                human_response=response,
                state=context.state,
            ),
            lease,
        )
    )
    return turn, started, dispatched, delivery


async def _ws_stop_turn(ws: WebSocket, team_id: str, hdr: dict, state: dict) -> None:
    if state.get("stop_requested", False):
        return
    active = state.get("active")
    if active is None or active.task.done():
        await ws.send_json({"type": "error", "status": 409, "detail": "no active chat turn"})
        return
    state["stop_requested"] = True
    queued = active.lease.cancel_if_queued()
    if queued or not active.dispatched.is_set():
        active.task.cancel()
        await asyncio.gather(active.task, return_exceptions=True)
        await ws.send_json({"type": "stopped"})
        return
    with contextlib.suppress(TimeoutError):
        await asyncio.wait_for(active.started.wait(), timeout=10)
    result = await _stop_delivery_once(team_id, hdr, active.delivery)
    if result is None:
        return
    status, data = result
    if status != 200 or not data.get("requested"):
        error_status = status if status != 200 else 409
        await ws.send_json(_upstream_error_event(error_status))


def _track_ws_turn(
    state: dict,
    tracked: tuple[asyncio.Task, asyncio.Event, asyncio.Event, _RelayDelivery],
    lease: _TurnLease,
) -> None:
    turn, started, dispatched, delivery = tracked
    active = _ActiveTurn(turn, started, dispatched, lease, delivery)
    state["stop_requested"] = False
    state["active"] = active

    def turn_done(_completed: asyncio.Task) -> None:
        lease.release()
        if state.get("active") is active:
            state["active"] = None

    turn.add_done_callback(turn_done)


async def _ws_human_response(
    ws: WebSocket,
    team_id: str,
    hdr: dict,
    msg: dict,
    state: dict,
) -> None:
    active = state.get("active")
    if active is not None and not active.task.done():
        await ws.send_json(
            {
                "type": "error",
                "status": 409,
                "detail": "team already has an active chat operation",
            }
        )
        return
    pending = state.get("pending_human")
    if not isinstance(pending, dict) or pending.get("challenge_id") != msg.get("challenge_id"):
        await ws.send_json(
            {
                "type": "error",
                "status": 409,
                "detail": "the human challenge is not pending",
            }
        )
        return
    try:
        canonical = chat_ws_contract.canonical_human_response(msg)
    except chat_ws_contract.FrameError as exc:
        await ws.send_json({"type": "error", "status": exc.status, "detail": exc.detail})
        return
    request = pending.get("request")
    if (
        canonical["decision"] == "submit"
        and isinstance(request, dict)
        and request.get("kind") in _HUMAN_AUTH_KINDS
        and team_contract.canonical_assurance_handle(canonical.get("value")) is None
    ):
        await ws.send_json(
            {
                "type": "error",
                "status": 400,
                "detail": "authentication response must be a one-use assurance handle",
            }
        )
        return
    lease = _TURN_ADMISSION.reserve()
    if lease is None:
        await ws.send_json(_relay_capacity_event())
        return
    response = {key: value for key, value in canonical.items() if key != "type"}
    try:
        tracked = _start_ws_human(_WsContext(ws, team_id, hdr, state), response, lease)
    except BaseException:
        lease.release()
        raise
    state["pending_human"] = None
    _track_ws_turn(state, tracked, lease)


async def _ws_dispatch(ws: WebSocket, team_id: str, hdr: dict, msg: dict, state: dict) -> None:
    if msg.get("type") == "chat":
        if state.get("pending_human") is not None:
            await ws.send_json(
                {
                    "type": "error",
                    "status": 409,
                    "detail": "a human challenge must be resolved before another turn",
                }
            )
            return
        try:
            if set(msg) != {"type", "message", "files", "assistant_ids"}:
                raise ClientPayloadError(
                    400,
                    "chat frame must contain only type, message, files, and assistant_ids",
                )
            turn_payload = _chat_turn_payload({key: value for key, value in msg.items() if key != "type"})
        except ClientPayloadError as exc:
            await ws.send_json({"type": "error", "status": exc.status, "detail": exc.detail})
            return
        msg = {"type": "chat", **turn_payload}
        active = state.get("active")
        if active is not None and not active.task.done():
            await ws.send_json(
                {
                    "type": "error",
                    "status": 409,
                    "detail": "team already has an active chat turn",
                }
            )
            return
        lease = _TURN_ADMISSION.reserve()
        if lease is None:
            await ws.send_json(
                {
                    "type": "error",
                    "status": 429,
                    "detail": "chat relay capacity reached",
                }
            )
            return
        # The background task keeps the socket responsive to Stop. The set is capped at one;
        # the controller independently enforces the same invariant across sockets.
        try:
            tracked = _start_ws_turn(_WsContext(ws, team_id, hdr, state), msg, lease)
        except BaseException:
            lease.release()
            raise
        _track_ws_turn(state, tracked, lease)
    elif msg.get("type") == "human-response":
        await _ws_human_response(ws, team_id, hdr, msg, state)
    elif msg.get("type") == "stop" and set(msg) == {"type"}:
        await _ws_stop_turn(ws, team_id, hdr, state)
    else:
        await ws.send_json({"type": "error", "status": 400, "detail": "unsupported chat frame"})


async def _ws_validate_opening(ws: WebSocket) -> bool:
    origin = ws.headers.get("origin")
    if not config.origin_allowed(origin, WS_ALLOWED_ORIGINS):
        log.warning("ws_origin_denied", origin=origin or "<missing>")
        await ws.close(code=4403)
        return False
    if tuple(ws.scope.get("subprotocols", ())) != (CHAT_WS_SUBPROTOCOL,):
        log.warning("ws_subprotocol_denied")
        await ws.close(code=4406)
        return False
    return True


async def _ws_identity(ws: WebSocket, team_id: str) -> tuple[str, str, str] | None:
    try:
        token, account_id = await _ws_verify(ws)
    except _ExecutorSaturatedError:
        await ws.close(code=4429)
        return None
    if not token:
        await ws.close(code=4401)
        return None
    canonical_team = team_contract.canonical_team_id(team_id)
    if canonical_team is None:
        await ws.close(code=4400)
        return None
    return token, account_id, canonical_team


router = APIRouter()


@router.websocket("/api/teams/{team_id}/chat/ws")
async def team_chat_ws(ws: WebSocket, team_id: str) -> None:
    if not await _ws_validate_opening(ws):
        return
    identity = await _ws_identity(ws, team_id)
    if identity is None:
        return
    token, account_id, team_id = identity
    connection = _WS_CONNECTION_ADMISSION.reserve(account_id, team_id)
    if connection is None:
        await ws.send(
            {
                "type": "websocket.http.response.start",
                "status": 429,
                "headers": [
                    (b"retry-after", b"1"),
                    (b"x-shimpz-rejection", b"websocket-capacity"),
                ],
            }
        )
        await ws.send(
            {
                "type": "websocket.http.response.body",
                "body": b"",
                "more_body": False,
            }
        )
        return
    try:
        await ws.accept(subprotocol=CHAT_WS_SUBPROTOCOL)
        hdr = {team_contract.ACCOUNT_SESSION_HEADER: token}
        state: dict = {
            "active": None,
            "stop_requested": False,
            "pending_human": None,
        }
        try:
            while True:
                try:
                    message = await _ws_receive_bounded_json(ws)
                except WebSocketPayloadError as exc:
                    await ws.send_json(
                        {
                            "type": "error",
                            "status": exc.status,
                            "detail": exc.detail,
                        }
                    )
                    await ws.close(code=exc.close_code)
                    return
                await _ws_dispatch(ws, team_id, hdr, message, state)
        except WebSocketDisconnect:
            return
        finally:
            active = state["active"]
            if active is not None:
                active.task.cancel()
                await asyncio.gather(active.task, return_exceptions=True)
            elif state["pending_human"] is not None:
                await _team_stop(team_id, hdr)
    finally:
        connection.release()
