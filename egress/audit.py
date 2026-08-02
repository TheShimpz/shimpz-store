"""Bounded Store-egress audit without OAuth or Access credential material."""

from __future__ import annotations

import json
import os
import stat
import threading
import time
import uuid
from pathlib import Path

AUDIT_PATH = Path("/var/log/store-egress/audit.jsonl")
MAX_BYTES = 10 * 1024 * 1024
BACKUPS = 3
SUBJECTS = frozenset({"neuron.shimpz.com:443", "rejected-target", "not-evaluated"})
_AUDIT_LOCK = threading.Lock()


class AuditError(OSError):
    """The Store egress security decision could not be recorded."""


def ensure_custody(path: Path = AUDIT_PATH) -> None:
    """Require one private, non-symlinked audit directory owned by this process."""
    try:
        metadata = path.parent.lstat()
    except OSError as exc:
        raise AuditError("Store egress audit custody is unavailable") from exc
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or path.parent.is_symlink()
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise AuditError("Store egress audit custody is unsafe")


def _rotate(path: Path) -> None:
    if not path.exists() or path.stat().st_size <= MAX_BYTES:
        return
    for index in range(BACKUPS - 1, 0, -1):
        source = path.with_name(f"{path.name}.{index}")
        target = path.with_name(f"{path.name}.{index + 1}")
        if source.exists():
            source.replace(target)
    path.replace(path.with_name(f"{path.name}.1"))


def record(*, result: str, code: int, reason: str, subject: str) -> str:
    """Persist one network-gated decision without request or credential content."""
    if result not in {"denied", "error", "ok"} or subject not in SUBJECTS:
        raise AuditError("invalid Store egress audit event")
    trace_id = uuid.uuid4().hex
    event = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "service": "store-egress",
        "trace_id": trace_id,
        "principal_class": "machine",
        "principal_id": "store",
        "operation": "connect",
        "subject": subject,
        "result": result,
        "code": code,
        "reason": reason,
    }
    encoded = (json.dumps(event, separators=(",", ":"), sort_keys=True) + "\n").encode()
    with _AUDIT_LOCK:
        try:
            ensure_custody(AUDIT_PATH)
            _rotate(AUDIT_PATH)
            descriptor = os.open(
                AUDIT_PATH,
                os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW,
                0o600,
            )
            try:
                if os.write(descriptor, encoded) != len(encoded):
                    raise AuditError("Store egress audit write was incomplete")
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except OSError as exc:
            raise AuditError("Store egress audit is unavailable") from exc
    return trace_id
