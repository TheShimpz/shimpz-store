"""Bounded account-session verification shared by Store routers."""

from __future__ import annotations

import os
import re
import stat
from contextlib import suppress

from fastapi import Request
from fastapi.responses import JSONResponse

from app.concurrency import BoundedThreadPoolExecutor
from app.concurrency import run_bounded as run_with_executor
from app.config import (
    ACCOUNT_COOKIE,
    ACCOUNT_URL,
    ACCOUNT_VERIFY_TOKEN_FILE,
    AUTH_QUEUE_MAX,
    AUTH_WORKER_THREADS,
    COOKIE_MAX_AGE,
)
from app.upstream import VERIFY_TIMEOUT_SECONDS, call

EXECUTOR = BoundedThreadPoolExecutor(
    max_workers=AUTH_WORKER_THREADS,
    max_outstanding=AUTH_WORKER_THREADS + AUTH_QUEUE_MAX,
    thread_name_prefix="shimpz-auth",
)
_CAPABILITY = re.compile(rb"[0-9a-f]{64}\Z")


def verification_capability() -> str:
    """Read one exact producer-owned Store capability without caching or logging it."""
    descriptor: int | None = None
    try:
        descriptor = os.open(
            ACCOUNT_VERIFY_TOKEN_FILE,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
        )
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o440:
                return ""
            raw = stream.read(65)
    except OSError, ValueError:
        return ""
    finally:
        if descriptor is not None:
            with suppress(OSError):
                os.close(descriptor)
    if _CAPABILITY.fullmatch(raw) is None:
        return ""
    return raw.decode("ascii")


async def run_bounded(fn, /, *args):
    return await run_with_executor(EXECUTOR, fn, *args)


def set_cookie(response: JSONResponse, token: str) -> None:
    response.set_cookie(
        ACCOUNT_COOKIE,
        token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="strict",
        secure=True,
        path="/",
    )


def authed_account(request: Request) -> tuple[str, str, str]:
    """Return the verified token/account/username tuple, or three empty strings."""
    token = request.cookies.get(ACCOUNT_COOKIE, "")
    if not token:
        return "", "", ""
    capability = verification_capability()
    if not capability:
        return "", "", ""
    status, data = call(
        ACCOUNT_URL,
        "POST",
        "/v1/verify",
        {"token": token},
        extra={"Authorization": f"Bearer {capability}"},
        timeout=VERIFY_TIMEOUT_SECONDS,
    )
    if status == 200 and data.get("account_id"):
        return token, data["account_id"], data.get("username", "")
    return "", "", ""


async def authed_account_bounded(request: Request) -> tuple[str, str, str]:
    return await run_bounded(authed_account, request)


def client_ip(request: Request) -> str:
    """Return Cloudflare's client IP when present, otherwise the socket peer."""
    return request.headers.get("cf-connecting-ip", "") or (request.client.host if request.client else "")
