"""Browser mutation and private-response policy for authenticated Store routes."""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import (
    ASSISTANT_MUTATION_ALLOWED_ORIGINS,
    PRIVATE_NO_STORE_HEADERS,
    origin_allowed,
)
from app.payloads import ClientPayloadError


def mutation_origin_allowed(origin: str | None) -> bool:
    return origin_allowed(origin, ASSISTANT_MUTATION_ALLOWED_ORIGINS)


def require_json_mutation(request: Request) -> None:
    """Admit a cookie-authenticated JSON mutation only from an allowed origin with a JSON body.

    A cross-site form or ``text/plain`` fetch is a simple request that skips the CORS preflight; requiring the JSON
    media type forces the preflight, and the origin check refuses what the browser still sends.
    """
    if not mutation_origin_allowed(request.headers.get("origin")):
        raise ClientPayloadError(403, "forbidden origin")
    media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media_type != "application/json":
        raise ClientPayloadError(415, "Content-Type must be application/json")


def private_json(content: dict, status_code: int = 200) -> JSONResponse:
    return JSONResponse(content, status_code=status_code, headers=PRIVATE_NO_STORE_HEADERS)
