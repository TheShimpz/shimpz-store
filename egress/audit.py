"""Bounded Store-egress audit without OAuth or Access credential material."""

from pathlib import Path

from audit_writer import AuditError, AuditWriter

AUDIT = AuditWriter(Path("/var/log/store-egress/audit.jsonl"), "store-egress")
SUBJECTS = frozenset({"neuron.shimpz.com:443", "rejected-target"})


def record(decision) -> str:
    """Persist one network-gated decision without request or credential content."""
    if decision.result not in {"denied", "error", "ok"} or decision.subject not in SUBJECTS:
        raise AuditError("invalid Store egress audit event")
    return AUDIT.write(
        {
            "principal_class": "machine",
            "principal_id": "store",
            "operation": "connect",
            "subject": decision.subject,
            "result": decision.result,
            "code": decision.code,
            "reason": decision.reason,
        }
    )
