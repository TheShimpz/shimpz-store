"""Logging house standard — structlog to JSON on stdout, one event per line, at INFO.

Call setup("<service>") ONCE at boot (main.py); everywhere else use structlog.get_logger(), never print() or the
stdlib logging module directly. Per-request trace_id is bound in app/middleware.py and rides every line automatically
(contextvars). The server's own loggers write the same JSON lines through JsonFormatter (app/logging.json).

No line carries an exception's message or a frame's values: an exception is logged by its class and, for the
application, the file, line, and function of each frame, because a message can quote a token, a header, or an
upstream reply.
"""

import json
import logging
import sys
import traceback
from datetime import UTC, datetime

import structlog

SERVICE = "shimpz-store"


def _exception_info(exc_info: object) -> tuple:
    if isinstance(exc_info, BaseException):
        return type(exc_info), exc_info, exc_info.__traceback__
    if isinstance(exc_info, tuple):
        return exc_info
    return sys.exc_info()


def exception_summary(_logger: object, _method: str, event_dict: dict) -> dict:
    """Replace a logged exception by its class and frame locations; its message and values never reach a line."""
    exc_info = event_dict.pop("exc_info", None)
    if not exc_info:
        return event_dict
    kind, _value, trace = _exception_info(exc_info)
    if kind is not None:
        event_dict["exception"] = kind.__name__
        event_dict["frames"] = [
            f"{frame.filename}:{frame.lineno}:{frame.name}" for frame in traceback.extract_tb(trace)
        ]
    return event_dict


def setup(service: str) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # inject per-request binds (trace_id, ...)
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts"),
            structlog.processors.StackInfoRenderer(),
            exception_summary,
            structlog.processors.EventRenamer("msg"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),  # stdout; the platform collector ships it
        cache_logger_on_first_use=True,
    )
    structlog.contextvars.bind_contextvars(service=service)


class JsonFormatter(logging.Formatter):
    """One JSON line per server record: its unformatted template, never its arguments or an exception's text."""

    def format(self, record: logging.LogRecord) -> str:
        line = {
            "ts": datetime.fromtimestamp(record.created, UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname.lower(),
            "service": SERVICE,
            "msg": record.msg if isinstance(record.msg, str) else type(record.msg).__name__,
        }
        if record.exc_info and record.exc_info[0] is not None:
            line["exception"] = record.exc_info[0].__name__
        return json.dumps(line, separators=(",", ":"))
