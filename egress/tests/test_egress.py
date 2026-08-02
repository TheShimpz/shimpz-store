"""Security contracts for the dedicated Store-to-Neuron CONNECT boundary."""

from __future__ import annotations

import importlib.util
import json
import socket
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit = _module("audit", ROOT / "audit.py")
with mock.patch.dict("sys.modules", {"audit": audit}):
    app = _module("store_egress_app", ROOT / "app.py")


class StoreEgressTests(unittest.TestCase):
    def test_only_exact_neuron_https_target_is_permitted(self) -> None:
        self.assertTrue(app.permitted("neuron.shimpz.com", 443))
        for host, port in (
            ("NEURON.SHIMPZ.COM", 443),
            ("neuron.shimpz.com.", 443),
            ("shimpz.com", 443),
            ("neuron.shimpz.com.evil.example", 443),
            ("neuron.shimpz.com", 80),
        ):
            with self.subTest(host=host, port=port):
                self.assertFalse(app.permitted(host, port))

    def test_admission_requires_the_exact_complete_connect_request(self) -> None:
        with mock.patch.object(app, "resolve_public", return_value=(socket.AF_INET, ("104.16.1.2", 443))):
            self.assertEqual(app._admit(app.EXACT_REQUEST), (200, "allowed", (socket.AF_INET, ("104.16.1.2", 443))))
        for payload in (
            None,
            b"GET https://neuron.shimpz.com/ HTTP/1.1\r\n\r\n",
            b"CONNECT neuron.shimpz.com:443 HTTP/1.0\r\n\r\n",
            app.EXACT_REQUEST.replace(b"443", b"80"),
            app.EXACT_REQUEST.replace(b"\r\n\r\n", b"Proxy-Authorization: secret\r\n\r\n"),
        ):
            with self.subTest(payload=payload):
                code, _reason, resolved = app._admit(payload)
                self.assertNotEqual(code, 200)
                self.assertIsNone(resolved)

    def test_resolution_rejects_private_and_mixed_answers(self) -> None:
        public = (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("104.16.1.2", 443))
        private = (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.2", 443))
        with mock.patch.object(app.socket, "getaddrinfo", return_value=[public]):
            self.assertEqual(app.resolve_public(app.ALLOWED_HOST, 443), (socket.AF_INET, ("104.16.1.2", 443)))
        for answers in ([private], [public, private], []):
            with self.subTest(answers=answers), mock.patch.object(app.socket, "getaddrinfo", return_value=answers):
                self.assertIsNone(app.resolve_public(app.ALLOWED_HOST, 443))

    def test_connect_uses_the_validated_address_without_reresolving(self) -> None:
        upstream = mock.Mock()
        with mock.patch.object(app.socket, "socket", return_value=upstream) as constructor:
            self.assertIs(app._connect_upstream((socket.AF_INET, ("104.16.1.2", 443))), upstream)
        constructor.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        upstream.connect.assert_called_once_with(("104.16.1.2", 443))

    def test_audit_is_bounded_and_contains_no_request_material(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            path = root / "audit.jsonl"
            with mock.patch.object(audit, "AUDIT_PATH", path):
                audit.record(result="ok", code=200, reason="allowed", subject="neuron.shimpz.com:443")
            event = json.loads(path.read_text())
            self.assertEqual(event["principal_id"], "store")
            self.assertEqual(event["subject"], "neuron.shimpz.com:443")
            self.assertNotIn("credential", event)
            self.assertNotIn("token", path.read_text().lower())
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_audit_rejects_unsafe_custody_and_unbounded_subjects(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o755)
            with self.assertRaises(audit.AuditError):
                audit.ensure_custody(root / "audit.jsonl")
        with self.assertRaises(audit.AuditError):
            audit.record(result="ok", code=200, reason="allowed", subject="attacker.example:443")

    def test_missing_audit_fails_startup_before_bind(self) -> None:
        with (
            mock.patch.object(audit, "ensure_custody", side_effect=audit.AuditError),
            mock.patch.object(app, "Server") as server,
        ):
            self.assertEqual(app.main(), 1)
        server.assert_not_called()


if __name__ == "__main__":
    unittest.main()
