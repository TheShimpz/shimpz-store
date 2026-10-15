"""Logging house standard — structlog to JSON on stdout, one event per line, at INFO.

Call setup("<service>") ONCE at boot (main.py); everywhere else use structlog.get_logger(), never print() or the
stdlib logging module directly. Per-request trace_id is bound in app/middleware.py and rides every line automatically
(contextvars).
"""

import logging

import structlog
import structlog.tracebacks


def setup(service: str) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # inject per-request binds (trace_id, ...)
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts"),
            structlog.processors.StackInfoRenderer(),
            # Full exception -> structured JSON, never a bare string. Exceptions keep their full stack, but never
            # frame locals: a request frame holds session tokens and upload bytes, which must not reach logs.
            structlog.processors.ExceptionRenderer(structlog.tracebacks.ExceptionDictTransformer(show_locals=False)),
            structlog.processors.EventRenamer("msg"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),  # stdout; the platform collector ships it
        cache_logger_on_first_use=True,
    )
    structlog.contextvars.bind_contextvars(service=service)
