"""Edge coverage for finite Store concurrency admission."""

from __future__ import annotations

import asyncio
import concurrent.futures

import pytest

from app.concurrency import BoundedThreadPoolExecutor, TurnAdmission, WsConnectionAdmission, run_bounded


@pytest.mark.parametrize(("workers", "outstanding"), [(0, 1), (2, 1)])
def test_bounded_executor_rejects_invalid_capacity(workers, outstanding):
    with pytest.raises(ValueError, match="capacity"):
        BoundedThreadPoolExecutor(
            max_workers=workers,
            max_outstanding=outstanding,
            thread_name_prefix="test",
        )


def test_bounded_executor_releases_permit_when_submission_fails(monkeypatch):
    executor = BoundedThreadPoolExecutor(
        max_workers=1,
        max_outstanding=1,
        thread_name_prefix="test",
    )

    def fail_submit(*_args, **_kwargs):
        raise RuntimeError("submission failed")

    monkeypatch.setattr(concurrent.futures.ThreadPoolExecutor, "submit", fail_submit)
    try:
        with pytest.raises(RuntimeError, match="submission failed"):
            executor.submit(lambda: None)
        assert executor._permits.acquire(blocking=False)
        executor._permits.release()
    finally:
        executor.shutdown(wait=True)


def test_run_bounded_returns_the_blocking_result():
    async def scenario() -> None:
        executor = BoundedThreadPoolExecutor(
            max_workers=1,
            max_outstanding=1,
            thread_name_prefix="test",
        )
        try:
            assert await run_bounded(executor, lambda left, right: left + right, 2, 3) == 5
        finally:
            executor.shutdown(wait=True)

    asyncio.run(scenario())


@pytest.mark.parametrize(("active", "queued"), [(0, 0), (1, -1)])
def test_turn_admission_rejects_invalid_limits(active, queued):
    with pytest.raises(ValueError, match="turn admission"):
        TurnAdmission(active, queued)


def test_turn_release_skips_stale_waiters_and_grant_is_idempotent():
    async def scenario() -> None:
        admission = TurnAdmission(1, 1)
        active = admission.reserve()
        stale = admission.reserve()
        assert active is not None and stale is not None
        active._grant()
        stale._state = "released"
        active.release()
        assert admission.snapshot() == (0, 0)
        assert active.cancel_if_queued() is False

    asyncio.run(scenario())


def test_turn_promotion_recovers_when_the_waiter_loop_is_closed():
    class ClosedLoop:
        def call_soon_threadsafe(self, *_args) -> None:
            raise RuntimeError("loop closed")

    async def scenario() -> None:
        admission = TurnAdmission(1, 1)
        active = admission.reserve()
        queued = admission.reserve()
        assert active is not None and queued is not None
        queued._loop = ClosedLoop()
        active.release()
        assert admission.snapshot() == (0, 0)
        assert queued._state == "released"

    asyncio.run(scenario())


def test_websocket_admission_rejects_nonpositive_limits():
    with pytest.raises(ValueError, match="positive"):
        WsConnectionAdmission(global_limit=1, account_limit=1, team_limit=0)


def test_websocket_release_preserves_nonzero_account_and_team_counts():
    admission = WsConnectionAdmission(global_limit=3, account_limit=3, team_limit=2)
    first = admission.reserve("account", "team")
    second = admission.reserve("account", "team")
    assert first is not None and second is not None
    first.release()
    assert admission.snapshot() == (1, {"account": 1}, {("account", "team"): 1})
    second.release()
    assert admission.snapshot() == (0, {}, {})
