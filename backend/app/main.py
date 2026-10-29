"""Serve the Shimpz public site, the public Assistant catalog, and the platform OAuth broker."""

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.concurrency import ExecutorSaturatedError as _ExecutorSaturatedError
from app.logconf import SERVICE, setup
from app.middleware import TraceIdMiddleware
from app.routers import oauth, public, static

setup(SERVICE)
log = structlog.get_logger()

fastapi_app = FastAPI(title="shimpz-store", docs_url=None, redoc_url=None, openapi_url=None)


@fastapi_app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    # Fail-loud: full structured trace in the logs, generic 500 to the caller. Never swallow.
    log.exception("unhandled_exception", path=request.url.path)
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


@fastapi_app.exception_handler(_ExecutorSaturatedError)
async def executor_saturated(request: Request, exc: _ExecutorSaturatedError) -> JSONResponse:
    log.warning("store_capacity_rejected", path=request.url.path)
    return JSONResponse(
        status_code=429,
        content={"detail": "Store upstream capacity reached"},
        headers={"Retry-After": "1"},
    )


fastapi_app.include_router(oauth.router)
fastapi_app.include_router(public.router)
fastapi_app.include_router(static.router)

# The header layer is the outermost ASGI layer, outside the error middleware that answers an unhandled exception, so
# every response, the 500 included, carries the security headers and the request id.
app = TraceIdMiddleware(fastapi_app)
