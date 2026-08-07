"""Security contracts for the dedicated Store-to-Neuron CONNECT boundary."""

from __future__ import annotations

import importlib.util
import json
import runpy
import socket
import socketserver
import stat
import sys
import tempfile
import threading
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
healthcheck = _module("store_egress_healthcheck", ROOT / "healthcheck.py")


class StoreEgressTests(unittest.TestCase):
    def test_wire_contract_is_pinned_independently_of_admission(self) -> None:
        self.assertEqual(
            app.EXACT_REQUEST,
            b"CONNECT neuron.shimpz.com:443 HTTP/1.1\r\nHost: neuron.shimpz.com:443\r\n\r\n",
        )
        stream = mock.Mock()
        app.Handler._reply(stream, 200)
        stream.sendall.assert_called_once_with(b"HTTP/1.1 200 Connection established\r\n\r\n")

    def test_admission_requires_the_exact_complete_connect_request(self) -> None:
        with mock.patch.object(app, "resolve_public", return_value=(socket.AF_INET, ("104.16.1.2", 443))):
            self.assertEqual(
                app._admit(app.EXACT_REQUEST),
                (200, "allowed", (socket.AF_INET, ("104.16.1.2", 443))),
            )
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
        with mock.patch.object(app, "resolve_public", return_value=None):
            self.assertEqual(app._admit(app.EXACT_REQUEST), (403, "destination-rejected", None))

    def test_resolution_rejects_private_and_mixed_answers(self) -> None:
        public = (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("104.16.1.2", 443))
        private = (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.2", 443))
        with mock.patch.object(app.socket, "getaddrinfo", return_value=[public]):
            self.assertEqual(
                app.resolve_public(app.ALLOWED_HOST, 443),
                (socket.AF_INET, ("104.16.1.2", 443)),
            )
        for answers in ([private], [public, private], []):
            with (
                self.subTest(answers=answers),
                mock.patch.object(app.socket, "getaddrinfo", return_value=answers),
            ):
                self.assertIsNone(app.resolve_public(app.ALLOWED_HOST, 443))

    def test_resolution_rejects_dns_and_malformed_answers(self) -> None:
        with mock.patch.object(app.socket, "getaddrinfo", side_effect=OSError("dns")):
            self.assertIsNone(app.resolve_public(app.ALLOWED_HOST, 443))
        malformed = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("invalid", 443))]
        with mock.patch.object(app.socket, "getaddrinfo", return_value=malformed):
            self.assertIsNone(app.resolve_public(app.ALLOWED_HOST, 443))

    def test_request_reader_handles_chunks_and_closed_inputs(self) -> None:
        complete = mock.Mock()
        complete.recv.side_effect = [b"CONNECT ", b"neuron\r\n\r\n"]
        self.assertEqual(app._read_request(complete), b"CONNECT neuron\r\n\r\n")

        for effect in (OSError("closed"), b""):
            with self.subTest(effect=effect):
                closed = mock.Mock()
                closed.recv.side_effect = effect if isinstance(effect, OSError) else None
                if not isinstance(effect, OSError):
                    closed.recv.return_value = effect
                self.assertIsNone(app._read_request(closed))

        oversized = mock.Mock()
        oversized.recv.return_value = b"x" * (app.MAX_REQUEST_BYTES + 1)
        self.assertIsNone(app._read_request(oversized))

    def test_connect_uses_the_validated_address_without_reresolving(self) -> None:
        upstream = mock.Mock()
        with mock.patch.object(app.socket, "socket", return_value=upstream) as constructor:
            self.assertIs(app._connect_upstream((socket.AF_INET, ("104.16.1.2", 443))), upstream)
        constructor.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        upstream.connect.assert_called_once_with(("104.16.1.2", 443))

    def test_upstream_connection_failures_close_partial_sockets(self) -> None:
        with mock.patch.object(app.socket, "socket", side_effect=OSError("closed")):
            self.assertIsNone(app._connect_upstream((socket.AF_INET, ("104.16.1.2", 443))))

        upstream = mock.Mock()
        upstream.connect.side_effect = OSError("closed")
        with mock.patch.object(app.socket, "socket", return_value=upstream):
            self.assertIsNone(app._connect_upstream((socket.AF_INET, ("104.16.1.2", 443))))
        upstream.close.assert_called_once_with()

    def test_audit_is_bounded_and_contains_no_request_material(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            path = root / "audit.jsonl"
            with mock.patch.object(audit, "AUDIT_PATH", path):
                audit.record(
                    result="ok",
                    code=200,
                    reason="allowed",
                    subject="neuron.shimpz.com:443",
                )
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

    def test_audit_rejects_missing_custody_and_rotates_bounded_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing" / "audit.jsonl"
            with self.assertRaisesRegex(audit.AuditError, "custody is unavailable"):
                audit.ensure_custody(missing)

            root = Path(directory)
            root.chmod(0o700)
            path = root / "audit.jsonl"
            path.write_text("current", encoding="utf-8")
            path.with_name("audit.jsonl.1").write_text("previous", encoding="utf-8")
            with mock.patch.object(audit, "MAX_BYTES", 1):
                audit._rotate(path)
            self.assertEqual(path.with_name("audit.jsonl.1").read_text(), "current")
            self.assertEqual(path.with_name("audit.jsonl.2").read_text(), "previous")

    def test_audit_write_failures_are_closed_and_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            path = root / "audit.jsonl"
            with (
                mock.patch.object(audit, "AUDIT_PATH", path),
                mock.patch.object(audit.os, "write", return_value=0),
                self.assertRaisesRegex(audit.AuditError, "unavailable"),
            ):
                audit.record(
                    result="denied",
                    code=403,
                    reason="closed",
                    subject="rejected-target",
                )

            with (
                mock.patch.object(audit, "AUDIT_PATH", path),
                mock.patch.object(audit.os, "open", side_effect=OSError("closed")),
                self.assertRaisesRegex(audit.AuditError, "unavailable"),
            ):
                audit.record(result="error", code=503, reason="closed", subject="not-evaluated")

    def test_missing_audit_fails_startup_before_bind(self) -> None:
        with (
            mock.patch.object(audit, "ensure_custody", side_effect=audit.AuditError),
            mock.patch.object(app, "Server") as server,
        ):
            self.assertEqual(app.main(), 1)
        server.assert_not_called()

    def test_capacity_denial_is_timed_audited_and_closed_on_accept_loop(self) -> None:
        server = object.__new__(app.Server)
        server._slots = threading.BoundedSemaphore(1)
        self.assertTrue(server._slots.acquire(blocking=False))
        server._source_guard = threading.Lock()
        server._source_counts = {}
        request = mock.Mock()
        with mock.patch.object(audit, "record") as record:
            server.process_request(request, ("172.20.0.2", 12345))

        request.settimeout.assert_called_once_with(app.CONNECT_TIMEOUT)
        record.assert_called_once_with(
            result="denied",
            code=503,
            reason="capacity",
            subject="not-evaluated",
        )
        request.sendall.assert_called_once_with(b"HTTP/1.1 503 Service Unavailable\r\n\r\n")
        request.close.assert_called_once_with()

    def test_handler_routes_incomplete_denied_and_allowed_requests(self) -> None:
        handler = object.__new__(app.Handler)
        handler.request = mock.Mock()
        with (
            mock.patch.object(app, "_read_request", return_value=None),
            mock.patch.object(handler, "_deny") as deny,
            mock.patch.object(handler, "_connect") as connect,
        ):
            handler.handle()
        deny.assert_not_called()
        connect.assert_not_called()

        with (
            mock.patch.object(app, "_read_request", return_value=b"wrong"),
            mock.patch.object(handler, "_deny") as deny,
        ):
            handler.handle()
        deny.assert_called_once_with(handler.request, 400, "request-rejected")

        resolved = (socket.AF_INET, ("104.16.1.2", 443))
        with (
            mock.patch.object(app, "_read_request", return_value=app.EXACT_REQUEST),
            mock.patch.object(app, "resolve_public", return_value=resolved),
            mock.patch.object(handler, "_connect") as connect,
        ):
            handler.handle()
        connect.assert_called_once_with(handler.request, resolved)

    def test_denial_and_connect_fail_closed_when_audit_is_unavailable(self) -> None:
        client = mock.Mock()
        with mock.patch.object(audit, "record", side_effect=audit.AuditError("closed")):
            app.Handler._deny(client, 400, "request-rejected")
        self.assertIn(b"HTTP/1.1 503", client.sendall.call_args.args[0])

        with (
            mock.patch.object(app, "_connect_upstream", return_value=None),
            mock.patch.object(app.Handler, "_deny") as deny,
        ):
            app.Handler._connect(client, (socket.AF_INET, ("104.16.1.2", 443)))
        deny.assert_called_once_with(client, 502, "upstream-unavailable")

        upstream = mock.Mock()
        with (
            mock.patch.object(app, "_connect_upstream", return_value=upstream),
            mock.patch.object(audit, "record", side_effect=audit.AuditError("closed")),
        ):
            app.Handler._connect(client, (socket.AF_INET, ("104.16.1.2", 443)))
        upstream.close.assert_called_once_with()

    def test_connect_audits_replies_and_tunnels_after_admission(self) -> None:
        client = mock.Mock()
        upstream = mock.Mock()
        with (
            mock.patch.object(app, "_connect_upstream", return_value=upstream),
            mock.patch.object(audit, "record") as record,
            mock.patch.object(app.Handler, "_reply") as reply,
            mock.patch.object(app.Handler, "_tunnel") as tunnel,
        ):
            app.Handler._connect(client, (socket.AF_INET, ("104.16.1.2", 443)))
        record.assert_called_once_with(
            result="ok",
            code=200,
            reason="allowed",
            subject="neuron.shimpz.com:443",
        )
        reply.assert_called_once_with(client, 200)
        tunnel.assert_called_once_with(client, upstream)

    def test_tunnel_forwards_both_directions_and_always_closes(self) -> None:
        first = mock.Mock()
        second = mock.Mock()
        first.recv.side_effect = [b"request", b""]
        second.recv.return_value = b"response"
        readable = [([first], [], []), ([second], [], []), ([first], [], [])]
        first.shutdown.side_effect = OSError("closed")
        with mock.patch.object(app.select, "select", side_effect=readable):
            app.Handler._tunnel(first, second)
        second.sendall.assert_called_once_with(b"request")
        first.sendall.assert_called_once_with(b"response")
        first.close.assert_called_once_with()
        second.close.assert_called_once_with()

        blocked = mock.Mock()
        peer = mock.Mock()
        with mock.patch.object(app.select, "select", return_value=([], [], [blocked])):
            app.Handler._tunnel(blocked, peer)

        with mock.patch.object(app.select, "select", side_effect=OSError("closed")):
            app.Handler._tunnel(mock.Mock(), mock.Mock())

    def test_server_releases_capacity_across_success_and_failure(self) -> None:
        server = app.Server(("127.0.0.1", 0), app.Handler, bind_and_activate=False)
        request = mock.Mock()
        try:
            with mock.patch.object(socketserver.ThreadingTCPServer, "process_request") as process:
                server.process_request(request, ("192.0.2.1", 1))
            process.assert_called_once_with(request, ("192.0.2.1", 1))
            self.assertEqual(server._source_counts, {"192.0.2.1": 1})
            server._release("192.0.2.1")

            with (
                mock.patch.object(
                    socketserver.ThreadingTCPServer,
                    "process_request",
                    side_effect=RuntimeError("closed"),
                ),
                self.assertRaisesRegex(RuntimeError, "closed"),
            ):
                server.process_request(request, ("192.0.2.2", 1))
            self.assertNotIn("192.0.2.2", server._source_counts)

            server._source_counts["192.0.2.3"] = 2
            server._slots = threading.BoundedSemaphore(2)
            self.assertTrue(server._slots.acquire(blocking=False))
            self.assertTrue(server._slots.acquire(blocking=False))
            server._release("192.0.2.3")
            self.assertEqual(server._source_counts["192.0.2.3"], 1)
            server._release("192.0.2.3")
        finally:
            server.server_close()

    def test_thread_release_and_per_source_capacity_are_fail_closed(self) -> None:
        server = object.__new__(app.Server)
        server._slots = threading.BoundedSemaphore(app.MAX_CONCURRENCY)
        server._source_guard = threading.Lock()
        server._source_counts = {"192.0.2.1": app.MAX_SOURCE_CONCURRENCY}
        request = mock.Mock()
        with mock.patch.object(audit, "record", side_effect=audit.AuditError("closed")):
            server.process_request(request, ("192.0.2.1", 1))
        request.close.assert_called_once_with()

        server._source_counts = {"192.0.2.2": 1}
        self.assertTrue(server._slots.acquire(blocking=False))
        with mock.patch.object(socketserver.ThreadingTCPServer, "process_request_thread") as process:
            server.process_request_thread(request, ("192.0.2.2", 1))
        process.assert_called_once_with(request, ("192.0.2.2", 1))
        self.assertNotIn("192.0.2.2", server._source_counts)

    def test_main_and_script_guard_close_the_server(self) -> None:
        for side_effect in (None, KeyboardInterrupt):
            server = mock.Mock()
            server.serve_forever.side_effect = side_effect
            with (
                self.subTest(side_effect=side_effect),
                mock.patch.object(audit, "ensure_custody"),
                mock.patch.object(app, "Server", return_value=server),
            ):
                self.assertEqual(app.main(), 0)
            server.server_close.assert_called_once_with()

        with (
            mock.patch.object(audit, "ensure_custody"),
            mock.patch.object(app, "Server", side_effect=OSError("bind")),
        ):
            self.assertEqual(app.main(), 1)

        with (
            mock.patch.dict(sys.modules, {"audit": audit}),
            mock.patch.object(audit, "ensure_custody", side_effect=audit.AuditError("closed")),
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
