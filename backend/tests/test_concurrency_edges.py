"""Edge coverage for finite Store worker admission."""

import asyncio
import concurrent.futures
import threading

import pytest

from app.concurrency import BoundedThreadPoolExecutor, ExecutorSaturatedError, run_bounded


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


def test_bounded_executor_refuses_work_beyond_its_outstanding_budget():
    executor = BoundedThreadPoolExecutor(
        max_workers=1,
        max_outstanding=1,
        thread_name_prefix="test",
    )
    release = threading.Event()
    try:
        running = executor.submit(release.wait)
        with pytest.raises(ExecutorSaturatedError):
            executor.submit(lambda: None)
        release.set()
        running.result()
    finally:
        release.set()
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
