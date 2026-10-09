"""Security contracts for the dedicated Store-to-Neuron CONNECT boundary.

The neutral CONNECT transport this profile runs is the umbrella `.egress/` (ADR-0104), proven once by
`.egress/tests`; these tests prove what Store owns: the exact request, its audit record, and its envelope.
"""

import contextlib
import importlib.util
import json
import runpy
import socket
import ssl
import stat
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1] / ".egress"))


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
healthcheck = _module("store_egress_healthcheck", ROOT / "healthcheck.py")
connect = app.connect


def _client_hello(server_name: str) -> bytes:
    """The first flight a real Python TLS client sends for `server_name`."""
    incoming, outgoing = ssl.MemoryBIO(), ssl.MemoryBIO()
    client = ssl.create_default_context().wrap_bio(incoming, outgoing, server_hostname=server_name)
    with contextlib.suppress(ssl.SSLWantReadError):
        client.do_handshake()
    return outgoing.read()


class StoreEgressTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.audit_path = Path(directory.name, "audit.jsonl")
        patcher = mock.patch.object(audit, "AUDIT", audit.AuditWriter(self.audit_path, "store-egress"))
        patcher.start()
        self.addCleanup(patcher.stop)

    def _records(self) -> list[dict]:
        if not self.audit_path.exists():
            return []
        return [json.loads(line) for line in self.audit_path.read_text(encoding="utf-8").splitlines()]

    def test_wire_contract_and_envelope_are_pinned(self) -> None:
        self.assertEqual(
            app.EXACT_REQUEST,
            b"CONNECT neuron.shimpz.com:443 HTTP/1.1\r\nHost: neuron.shimpz.com:443\r\n\r\n",
        )
        self.assertEqual(
            (app.Handler.connect_timeout, app.Handler.idle_timeout, app.Handler.request_limit), (10, 30, 1024)
        )
        self.assertEqual(
            (app.Server.max_concurrency, app.Server.max_source_concurrency, app.Server.request_queue_size), (8, 8, 8)
        )

    def test_admission_requires_the_exact_complete_connect_request(self) -> None:
        handler = object.__new__(app.Handler)
        self.assertEqual(handler.admit(app.EXACT_REQUEST), connect.Target("neuron.shimpz.com", 443))
        for payload in (
            b"GET https://neuron.shimpz.com/ HTTP/1.1\r\n\r\n",
            b"CONNECT neuron.shimpz.com:443 HTTP/1.0\r\n\r\n",
            app.EXACT_REQUEST.replace(b"443", b"80"),
            app.EXACT_REQUEST.replace(b"\r\n\r\n", b"\r\nProxy-Authorization: secret\r\n\r\n"),
            app.EXACT_REQUEST + b"\x16\x03\x01",
        ):
            with self.subTest(payload=payload):
                self.assertEqual(
                    handler.admit(payload), connect.Decision("denied", 400, "request-rejected", "rejected-target")
                )

    def _tunnel(self, request: bytes, flight: bytes) -> tuple[bytes, bytes]:
        """Serve one real connection to a local stand-in for Neuron; return what the client and upstream saw."""
        listener = socket.create_server(("127.0.0.1", 0))
        self.addCleanup(listener.close)
        listener.settimeout(5)
        handler_socket, client_socket = socket.socketpair()
        self.addCleanup(client_socket.close)
        self.addCleanup(handler_socket.close)
        with mock.patch.object(connect, "resolve_public", return_value=((socket.AF_INET, listener.getsockname()),)):
            worker = threading.Thread(target=app.Handler, args=(handler_socket, ("172.20.0.2", 1), mock.Mock()))
            worker.start()
            client_socket.settimeout(5)
            client_socket.sendall(request)
            response = client_socket.recv(512)
            received = b""
            if response.startswith(b"HTTP/1.1 200"):
                upstream, _peer = listener.accept()
                self.addCleanup(upstream.close)
                upstream.settimeout(5)
                client_socket.sendall(flight)
                while len(received) < len(flight) and (chunk := upstream.recv(65536)):
                    received += chunk
            client_socket.shutdown(socket.SHUT_WR)
            worker.join(10)
        self.assertFalse(worker.is_alive())
        return response, received

    def test_a_client_hello_naming_neuron_is_relayed_after_one_recorded_admission(self) -> None:
        flight = _client_hello("neuron.shimpz.com")
        response, received = self._tunnel(app.EXACT_REQUEST, flight)
        self.assertTrue(response.startswith(b"HTTP/1.1 200"))
        self.assertEqual(received, flight)
        records = self._records()
        self.assertEqual(
            [(record["result"], record["code"], record["reason"], record["subject"]) for record in records],
            [("ok", 200, "allowed", "neuron.shimpz.com:443")],
        )
        self.assertEqual((records[0]["principal_class"], records[0]["principal_id"]), ("machine", "store"))
        self.assertEqual(stat.S_IMODE(self.audit_path.stat().st_mode), 0o600)

    def test_a_fronted_server_name_and_a_wrong_request_are_recorded_without_request_material(self) -> None:
        response, received = self._tunnel(app.EXACT_REQUEST, _client_hello("example.com"))
        self.assertTrue(response.startswith(b"HTTP/1.1 200"))
        self.assertEqual(received, b"")
        self.assertEqual(self._records()[-1]["reason"], "sni-mismatch")
        self.assertEqual(self._records()[-1]["subject"], "neuron.shimpz.com:443")

        secret = app.EXACT_REQUEST.replace(b"\r\n\r\n", b"\r\nProxy-Authorization: secret\r\n\r\n")
        response, _received = self._tunnel(secret, b"")
        self.assertTrue(response.startswith(b"HTTP/1.1 400"))
        self.assertEqual(self._records()[-1]["subject"], "rejected-target")
        self.assertNotIn("secret", self.audit_path.read_text(encoding="utf-8"))

    def test_audit_admits_only_its_bounded_schema(self) -> None:
        self.assertEqual(audit.AUDIT.service, "store-egress")
        for decision in (
            connect.Decision("ok", 200, "allowed", "attacker.example:443"),
            connect.Decision("ok", 200, "allowed", "not-evaluated"),
            connect.Decision("other", 200, "allowed", "neuron.shimpz.com:443"),
        ):
            with self.subTest(decision=decision), self.assertRaises(audit.AuditError):
                audit.record(decision)
        self.assertEqual(self._records(), [])

    def test_main_fails_before_bind_without_audit_custody_and_closes_the_server(self) -> None:
        with (
            mock.patch.object(audit.AUDIT, "ensure_custody", side_effect=audit.AuditError("unsafe")),
            mock.patch.object(app, "Server") as server,
        ):
            self.assertEqual(app.main(), 1)
        server.assert_not_called()

        for side_effect in (None, KeyboardInterrupt):
            server = mock.Mock()
            server.serve_forever.side_effect = side_effect
            with (
                self.subTest(side_effect=side_effect),
                mock.patch.object(audit.AUDIT, "ensure_custody"),
                mock.patch.object(app, "Server", return_value=server),
            ):
                self.assertEqual(app.main(), 0)
            server.server_close.assert_called_once_with()

        with (
            mock.patch.object(audit.AUDIT, "ensure_custody"),
            mock.patch.object(app, "Server", side_effect=OSError("bind")),
        ):
            self.assertEqual(app.main(), 1)

        with (
            mock.patch.dict(sys.modules, {"audit": audit}),
            mock.patch.object(audit.AUDIT, "ensure_custody", side_effect=audit.AuditError("closed")),
            self.assertRaises(SystemExit) as raised,
        ):
            runpy.run_path(str(ROOT / "app.py"), run_name="__main__")
        self.assertEqual(raised.exception.code, 1)

    def test_healthcheck_reports_listener_state_and_script_status(self) -> None:
        connection = mock.MagicMock()
        with mock.patch.object(healthcheck.socket, "create_connection", return_value=connection):
            self.assertEqual(healthcheck.main(), 0)
        connection.__enter__.assert_called_once_with()

        with mock.patch.object(healthcheck.socket, "create_connection", side_effect=OSError("closed")):
            self.assertEqual(healthcheck.main(), 1)

        previous = sys.modules.get("store_egress_healthcheck")
        try:
            with (
                mock.patch.object(socket, "create_connection", side_effect=OSError("closed")),
                self.assertRaises(SystemExit) as raised,
            ):
                runpy.run_path(str(ROOT / "healthcheck.py"), run_name="__main__")
            self.assertEqual(raised.exception.code, 1)
        finally:
            if previous is not None:
                sys.modules["store_egress_healthcheck"] = previous


if __name__ == "__main__":
    unittest.main()
