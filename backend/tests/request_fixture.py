"""One-shot ASGI request and Account-session stand-ins shared by Store route and payload suites."""

import secrets

from fastapi import Request


def one_shot_request(body: bytes, headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    """Return a request that delivers body once and then reports a client disconnect."""
    delivered = False

    async def receive() -> dict[str, object]:
        nonlocal delivered
        if delivered:
            return {"type": "http.disconnect"}
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request({"type": "http", "headers": headers or []}, receive)


def session(authenticated: bool = True):
    """Return an ``authn.authed_account_bounded`` stand-in for a fresh signed-in or anonymous session."""
    token = secrets.token_hex(16) if authenticated else ""

    async def current(_request):
        return token, "account" if token else "", "user" if token else ""

    return current
