"""Logging house standard — structlog to JSON on stdout, one event per line.

Call setup("<service>") ONCE at boot (main.py); everywhere else use structlog.get_logger(). Never
print(), never the stdlib logging module directly — the shimpz-stdcheck gate BLOCKs both. Per-request
trace_id is bound in app/middleware.py and rides every line automatically (contextvars). LOG_FORMAT=console
gives human output in dev (default json); LOG_LEVEL sets the level (default INFO).
"""

import logging
import os

import structlog
import structlog.tracebacks


def setup(service: str) -> None:
    # Fail-fast: an invalid LOG_LEVEL must surface LOUDLY, never silently coerce to INFO (a masked
    # misconfiguration is exactly the fallback the house rules forbid).
    _lvl = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, _lvl, None)
    if not isinstance(level, int):
        raise ValueError(f"invalid LOG_LEVEL={_lvl!r} (use DEBUG/INFO/WARNING/ERROR/CRITICAL)")
    shared = [
        structlog.contextvars.merge_contextvars,  # inject per-request binds (trace_id, ...)
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts"),
        structlog.processors.StackInfoRenderer(),
    ]
    # Exceptions keep their full stack, but never frame locals: a request frame holds session tokens and upload
    # bytes, which must not reach logs.
    if os.getenv("LOG_FORMAT", "json") == "console":
        processors = [
            *shared,
            structlog.dev.ConsoleRenderer(exception_formatter=structlog.dev.plain_traceback),
        ]
    else:
        processors = [
            *shared,
            # Full exception -> structured JSON, never a bare string.
            structlog.processors.ExceptionRenderer(structlog.tracebacks.ExceptionDictTransformer(show_locals=False)),
            structlog.processors.EventRenamer("msg"),
            structlog.processors.JSONRenderer(),
        ]
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),  # stdout; the platform collector ships it
        cache_logger_on_first_use=True,
    )
    structlog.contextvars.bind_contextvars(service=service)
