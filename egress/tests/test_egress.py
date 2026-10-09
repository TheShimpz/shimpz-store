"""Security contracts for the dedicated Store-to-Neuron CONNECT boundary."""

import contextlib
import importlib.util
import json
import runpy
import socket
import socketserver
import ssl
import stat
import sys
import tempfile
import threading
import time
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
client_hello = _module("client_hello", ROOT / "client_hello.py")
with mock.patch.dict("sys.modules", {"audit": audit, "client_hello": client_hello}):
    app = _module("store_egress_app", ROOT / "app.py")
healthcheck = _module("store_egress_healthcheck", ROOT / "healthcheck.py")


def _client_hello(server_name: str) -> bytes:
    """The first flight a real Python TLS client sends for `server_name`."""
    incoming, outgoing = ssl.MemoryBIO(), ssl.MemoryBIO()
    client = ssl.create_default_context().wrap_bio(incoming, outgoing, server_hostname=server_name)
    with contextlib.suppress(ssl.SSLWantReadError):
        client.do_handshake()
    return outgoing.read()


def _later() -> float:
    return time.monotonic() + app.CONNECT_TIMEOUT


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
        with mock.patch.object(app, "resolve_public", return_value=((socket.AF_INET, ("104.16.1.2", 443)),)):
            self.assertEqual(
                app._admit(app.EXACT_REQUEST, _later()),
                (200, "allowed", ((socket.AF_INET, ("104.16.1.2", 443)),)),
            )
        for payload in (
            None,
            b"GET https://neuron.shimpz.com/ HTTP/1.1\r\n\r\n",
            b"CONNECT neuron.shimpz.com:443 HTTP/1.0\r\n\r\n",
            app.EXACT_REQUEST.replace(b"443", b"80"),
            app.EXACT_REQUEST.replace(b"\r\n\r\n", b"Proxy-Authorization: secret\r\n\r\n"),
        ):
            with self.subTest(payload=payload):
                code, _reason, resolved = app._admit(payload, _later())
                self.assertNotEqual(code, 200)
                self.assertIsNone(resolved)
        with mock.patch.object(app, "resolve_public", return_value=None):
            self.assertEqual(app._admit(app.EXACT_REQUEST, _later()), (403, "destination-rejected", None))

    def test_resolution_rejects_private_and_mixed_answers(self) -> None:
        public = (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("104.16.1.2", 443))
        private = (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.2", 443))
        with mock.patch.object(app.socket, "getaddrinfo", return_value=[public]):
            self.assertEqual(
                app.resolve_public(app.ALLOWED_HOST, 443, _later()),
                ((socket.AF_INET, ("104.16.1.2", 443)),),
            )
        second = (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("104.16.1.3", 443))
        with mock.patch.object(app.socket, "getaddrinfo", return_value=[public, second]):
            self.assertEqual(
                app.resolve_public(app.ALLOWED_HOST, 443, _later()),
                ((socket.AF_INET, ("104.16.1.2", 443)), (socket.AF_INET, ("104.16.1.3", 443))),
            )
        for answers in ([private], [public, private], []):
            with (
                self.subTest(answers=answers),
                mock.patch.object(app.socket, "getaddrinfo", return_value=answers),
            ):
                self.assertIsNone(app.resolve_public(app.ALLOWED_HOST, 443, _later()))

    def test_resolution_rejects_dns_and_malformed_answers(self) -> None:
        with mock.patch.object(app.socket, "getaddrinfo", side_effect=OSError("dns")):
            self.assertIsNone(app.resolve_public(app.ALLOWED_HOST, 443, _later()))
        malformed = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("invalid", 443))]
        with mock.patch.object(app.socket, "getaddrinfo", return_value=malformed):
            self.assertIsNone(app.resolve_public(app.ALLOWED_HOST, 443, _later()))

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

    def test_request_reader_closes_a_byte_trickle_at_its_absolute_deadline(self) -> None:
        # Each byte resets an idle timeout, so only a whole-read deadline stops a trickle holding a worker.
        trickle = mock.Mock()
        trickle.recv.side_effect = [b"CONNECT neuron.shimpz.com:443 HTTP/1.1\r\n", b"\r\n"]
        clock = [0.0, 0.0, app.CONNECT_TIMEOUT + 1.0]
        with mock.patch.object(app.time, "monotonic", side_effect=clock):
            self.assertIsNone(app._read_request(trickle))
        trickle.recv.assert_called_once()
        trickle.settimeout.assert_called_once_with(app.CONNECT_TIMEOUT)

        remaining = mock.Mock()
        remaining.recv.side_effect = [b"CONNECT ", b"neuron\r\n\r\n"]
        with mock.patch.object(app.time, "monotonic", side_effect=[0.0, 0.0, 4.0]):
            self.assertEqual(app._read_request(remaining), b"CONNECT neuron\r\n\r\n")
        self.assertEqual(
            remaining.settimeout.call_args_list,
            [mock.call(app.CONNECT_TIMEOUT), mock.call(app.CONNECT_TIMEOUT - 4.0)],
        )

    def test_connect_uses_the_validated_address_without_reresolving(self) -> None:
        upstream = mock.Mock()
        with mock.patch.object(app.socket, "socket", return_value=upstream) as constructor:
            self.assertIs(app._connect_upstream(((socket.AF_INET, ("104.16.1.2", 443)),), _later()), upstream)
        constructor.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        upstream.connect.assert_called_once_with(("104.16.1.2", 443))

    TWO_ADDRESSES = ((socket.AF_INET, ("104.16.1.2", 443)), (socket.AF_INET, ("104.16.1.3", 443)))

    def test_a_refused_first_address_falls_through_to_the_second(self) -> None:
        refused, live = mock.Mock(), mock.Mock()
        refused.connect.side_effect = ConnectionRefusedError("refused")
        with mock.patch.object(app.socket, "socket", side_effect=[refused, live]):
            self.assertIs(app._connect_upstream(self.TWO_ADDRESSES, _later()), live)
        refused.connect.assert_called_once_with(("104.16.1.2", 443))
        refused.close.assert_called_once_with()
        live.connect.assert_called_once_with(("104.16.1.3", 443))
        live.close.assert_not_called()

    def test_every_refused_address_yields_the_existing_upstream_failure(self) -> None:
        upstreams = [mock.Mock(), mock.Mock()]
        for upstream in upstreams:
            upstream.connect.side_effect = ConnectionRefusedError("refused")
        client = mock.Mock()
        with (
            mock.patch.object(app.socket, "socket", side_effect=upstreams),
            mock.patch.object(audit, "record") as record,
        ):
            app.Handler._connect(client, self.TWO_ADDRESSES, _later())
        record.assert_called_once_with(
            result="error",
            code=502,
            reason="upstream-unavailable",
            subject="neuron.shimpz.com:443",
        )
        client.sendall.assert_called_once_with(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
        for upstream in upstreams:
            upstream.close.assert_called_once_with()

    def test_a_mixed_public_private_answer_is_refused_before_any_connection(self) -> None:
        answers = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("104.16.1.2", 443)),
            (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("fd00::2", 443, 0, 0)),
        ]
        with (
            mock.patch.object(app.socket, "getaddrinfo", return_value=answers),
            mock.patch.object(app.socket, "socket") as constructor,
        ):
            self.assertEqual(app._admit(app.EXACT_REQUEST, _later()), (403, "destination-rejected", None))
        constructor.assert_not_called()

    def test_attempts_share_one_total_connect_deadline(self) -> None:
        slow, unused = mock.Mock(), mock.Mock()
        slow.connect.side_effect = TimeoutError("timed out")
        clock = iter([50.0, 50.0 + app.CONNECT_TIMEOUT])
        with (
            mock.patch.object(app.time, "monotonic", side_effect=lambda: next(clock)),
            mock.patch.object(app.socket, "socket", side_effect=[slow, unused]) as constructor,
        ):
            self.assertIsNone(app._connect_upstream(self.TWO_ADDRESSES, 50.0 + app.CONNECT_TIMEOUT))
        slow.settimeout.assert_called_once_with(app.CONNECT_TIMEOUT)
        constructor.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        unused.connect.assert_not_called()

    def test_a_real_refused_endpoint_falls_through_to_a_live_one(self) -> None:
        listener = socket.create_server(("127.0.0.1", 0))
        self.addCleanup(listener.close)
        closed = socket.create_server(("127.0.0.1", 0))
        refused_port = closed.getsockname()[1]
        closed.close()
        live = listener.getsockname()

        upstream = app._connect_upstream(
            ((socket.AF_INET, ("127.0.0.1", refused_port)), (socket.AF_INET, live)), _later()
        )
        self.assertIsNotNone(upstream)
        self.addCleanup(upstream.close)
        accepted, _peer = listener.accept()
        accepted.close()

        self.assertEqual(upstream.getpeername(), live)

    ANSWER = ((socket.AF_INET, socket.SOCK_STREAM, 6, "", ("104.16.1.2", 443)),)

    def _isolate_resolver(self) -> None:
        """Give the test a private one-slot resolver so a stuck lookup never reaches the shared pool."""
        self.slots = threading.BoundedSemaphore(1)
        self.release = threading.Event()
        self.addCleanup(self.release.set)
        patcher = mock.patch.object(app, "_RESOLVER_SLOTS", self.slots)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _stuck_lookup(self, *_args, **_kwargs) -> list:
        self.release.wait(5)
        return list(self.ANSWER)

    @staticmethod
    def _handle_exact_request(lookup: object, upstream: mock.Mock) -> tuple[mock.Mock, mock.Mock]:
        handler = object.__new__(app.Handler)
        handler.request = mock.Mock()
        with (
            mock.patch.object(app, "_read_request", return_value=app.EXACT_REQUEST),
            mock.patch.object(app.socket, "getaddrinfo", side_effect=lookup),
            mock.patch.object(app.socket, "socket", return_value=upstream),
            mock.patch.object(app.Handler, "_tunnel"),
            mock.patch.object(client_hello, "admit", return_value=b""),
            mock.patch.object(audit, "record") as record,
        ):
            handler.handle()
        return handler.request, record

    def test_slow_resolution_beyond_the_deadline_gets_the_existing_denial(self) -> None:
        self._isolate_resolver()
        never = mock.Mock()
        with mock.patch.object(app, "CONNECT_TIMEOUT", 0.05):
            client, record = self._handle_exact_request(self._stuck_lookup, never)

        client.sendall.assert_called_once_with(b"HTTP/1.1 403 Forbidden\r\n\r\n")
        record.assert_called_once_with(
            result="denied", code=403, reason="destination-rejected", subject="rejected-target"
        )
        self.assertEqual(never.method_calls, [])

    def test_resolution_and_connect_share_one_budget(self) -> None:
        self._isolate_resolver()
        for spent, expected in ((6.0, b"HTTP/1.1 200"), (app.CONNECT_TIMEOUT, b"HTTP/1.1 502")):
            with self.subTest(spent=spent):
                now = [100.0]

                def slow_lookup(*_args, spent=spent, now=now, **_kwargs) -> list:
                    now[0] += spent
                    return list(self.ANSWER)

                upstream = mock.Mock()
                with mock.patch.object(app.time, "monotonic", side_effect=lambda now=now: now[0]):
                    client, _record = self._handle_exact_request(slow_lookup, upstream)

                self.assertTrue(client.sendall.call_args.args[0].startswith(expected))
                if spent < app.CONNECT_TIMEOUT:
                    self.assertEqual(upstream.settimeout.call_args_list[0], mock.call(app.CONNECT_TIMEOUT - spent))
                else:
                    self.assertEqual(upstream.method_calls, [])

    def test_a_waiter_past_the_deadline_is_denied_without_resolving(self) -> None:
        self._isolate_resolver()
        with mock.patch.object(app.socket, "getaddrinfo", side_effect=self._stuck_lookup) as lookup:
            self.assertIsNone(app.resolve_public(app.ALLOWED_HOST, 443, time.monotonic() + 0.05))
            started = time.monotonic()
            self.assertIsNone(app.resolve_public(app.ALLOWED_HOST, 443, started + 0.2))
            self.assertGreaterEqual(time.monotonic() - started, 0.1)
        lookup.assert_called_once()

    def test_a_waiter_gets_the_permit_once_a_lookup_finishes_within_the_deadline(self) -> None:
        self._isolate_resolver()
        with mock.patch.object(app.socket, "getaddrinfo", side_effect=self._stuck_lookup):
            self.assertIsNone(app.resolve_public(app.ALLOWED_HOST, 443, time.monotonic() + 0.05))
        finish = threading.Timer(0.1, self.release.set)
        self.addCleanup(finish.cancel)
        with mock.patch.object(app.socket, "getaddrinfo", return_value=list(self.ANSWER)) as answered:
            finish.start()
            self.assertEqual(app.resolve_public(app.ALLOWED_HOST, 443, _later()), (self.ANSWER[0][0::4],))
        self.assertTrue(self.release.is_set())
        answered.assert_called_once()

    def test_a_resolver_thread_that_cannot_start_returns_its_permit(self) -> None:
        self._isolate_resolver()
        with (
            mock.patch.object(app.threading.Thread, "start", side_effect=RuntimeError("can't start new thread")),
            mock.patch.object(app.socket, "getaddrinfo", return_value=list(self.ANSWER)) as lookup,
        ):
            for _attempt in range(2):
                self.assertIsNone(app.resolve_public(app.ALLOWED_HOST, 443, _later()))
        lookup.assert_not_called()
        with mock.patch.object(app.socket, "getaddrinfo", return_value=list(self.ANSWER)):
            self.assertEqual(app.resolve_public(app.ALLOWED_HOST, 443, _later()), (self.ANSWER[0][0::4],))

    def test_upstream_connection_failures_close_partial_sockets(self) -> None:
        with mock.patch.object(app.socket, "socket", side_effect=OSError("closed")):
            self.assertIsNone(app._connect_upstream(((socket.AF_INET, ("104.16.1.2", 443)),), _later()))

        upstream = mock.Mock()
        upstream.connect.side_effect = OSError("closed")
        with mock.patch.object(app.socket, "socket", return_value=upstream):
            self.assertIsNone(app._connect_upstream(((socket.AF_INET, ("104.16.1.2", 443)),), _later()))
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

        resolved = ((socket.AF_INET, ("104.16.1.2", 443)),)
        with (
            mock.patch.object(app, "_read_request", return_value=app.EXACT_REQUEST),
            mock.patch.object(app, "resolve_public", return_value=resolved),
            mock.patch.object(handler, "_connect") as connect,
        ):
            handler.handle()
        connect.assert_called_once_with(handler.request, resolved, mock.ANY)

    def test_denial_and_connect_fail_closed_when_audit_is_unavailable(self) -> None:
        client = mock.Mock()
        with mock.patch.object(audit, "record", side_effect=audit.AuditError("closed")):
            app.Handler._deny(client, 400, "request-rejected")
        self.assertIn(b"HTTP/1.1 503", client.sendall.call_args.args[0])

        with (
            mock.patch.object(app, "_connect_upstream", return_value=None),
            mock.patch.object(app.Handler, "_deny") as deny,
        ):
            app.Handler._connect(client, ((socket.AF_INET, ("104.16.1.2", 443)),), _later())
        deny.assert_called_once_with(client, 502, "upstream-unavailable")

        upstream = mock.Mock()
        with (
            mock.patch.object(app, "_connect_upstream", return_value=upstream),
            mock.patch.object(audit, "record", side_effect=audit.AuditError("closed")),
        ):
            app.Handler._connect(client, ((socket.AF_INET, ("104.16.1.2", 443)),), _later())
        upstream.close.assert_called_once_with()

    def test_connect_audits_replies_and_tunnels_after_admission(self) -> None:
        client = mock.Mock()
        upstream = mock.Mock()
        with (
            mock.patch.object(app, "_connect_upstream", return_value=upstream),
            mock.patch.object(audit, "record") as record,
            mock.patch.object(app.Handler, "_reply") as reply,
            mock.patch.object(app.Handler, "_tunnel") as tunnel,
            mock.patch.object(client_hello, "admit", return_value=b"hello"),
        ):
            app.Handler._connect(client, ((socket.AF_INET, ("104.16.1.2", 443)),), _later())
        record.assert_called_once_with(
            result="ok",
            code=200,
            reason="allowed",
            subject="neuron.shimpz.com:443",
        )
        reply.assert_called_once_with(client, 200)
        upstream.sendall.assert_called_once_with(b"hello")
        tunnel.assert_called_once_with(client, upstream)

    def _tunnel(self, flight: bytes) -> tuple[bytes, bytes, list[dict]]:
        """Run a real handler, client, and upstream; return what the client and the upstream saw, and the audit."""
        listener = socket.create_server(("127.0.0.1", 0))
        self.addCleanup(listener.close)
        listener.settimeout(5)
        client, proxy = socket.socketpair()
        self.addCleanup(client.close)
        with tempfile.TemporaryDirectory() as directory:
            audit_path = Path(directory, "audit", "audit.jsonl")
            audit_path.parent.mkdir(mode=0o700)
            with (
                mock.patch.object(audit, "AUDIT_PATH", audit_path),
                mock.patch.object(app, "resolve_public", return_value=((socket.AF_INET, listener.getsockname()),)),
            ):
                worker = threading.Thread(target=app.Handler, args=(proxy, ("10.0.0.2", 1), None))
                worker.start()
                client.sendall(app.EXACT_REQUEST)
                client.settimeout(5)
                response = client.recv(256)
                upstream, _peer = listener.accept()
                self.addCleanup(upstream.close)
                upstream.settimeout(5)
                client.sendall(flight)
                received = b""
                while len(received) < len(flight) and (chunk := upstream.recv(65536)):
                    received += chunk
                if received:
                    client.sendall(b"application data")
                    received += upstream.recv(64)
                client.shutdown(socket.SHUT_WR)
                worker.join(10)
            documents = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
        self.assertFalse(worker.is_alive())
        self.assertTrue(response.startswith(b"HTTP/1.1 200"))
        return client.recv(64), received, documents

    def test_a_client_hello_naming_neuron_is_relayed_unchanged(self) -> None:
        flight = _client_hello("neuron.shimpz.com")
        to_client, upstream_saw, documents = self._tunnel(flight)

        self.assertEqual(upstream_saw, flight + b"application data")
        self.assertEqual(to_client, b"")
        self.assertEqual([(document["result"], document["reason"]) for document in documents], [("ok", "allowed")])

    def test_a_fronted_or_non_tls_server_name_is_refused_and_audited_without_relaying(self) -> None:
        for flight, reason in (
            (_client_hello("api.cloudflare.com"), "sni-mismatch"),
            (b"PRI * HTTP/2.0", "tls-required"),
        ):
            with self.subTest(reason=reason):
                to_client, upstream_saw, documents = self._tunnel(flight)

                self.assertEqual((upstream_saw, to_client), (b"", b""))
                refusal = documents[-1]
                self.assertEqual(
                    (refusal["result"], refusal["code"], refusal["reason"], refusal["subject"]),
                    ("denied", 403, reason, "neuron.shimpz.com:443"),
                )
                self.assertNotIn("api.cloudflare.com", json.dumps(documents))

    def test_an_unrecordable_refusal_or_failed_first_flight_still_closes_unspliced(self) -> None:
        client, upstream = mock.Mock(), mock.Mock()
        with (
            mock.patch.object(client_hello, "admit", side_effect=client_hello.RefusalError("ech-refused")),
            mock.patch.object(audit, "record", side_effect=audit.AuditError("closed")) as record,
            mock.patch.object(app.Handler, "_tunnel") as tunnel,
        ):
            app.Handler._relay(client, upstream)
        record.assert_called_once()
        upstream.sendall.assert_not_called()
        for stream in (client, upstream):
            stream.close.assert_called_once_with()
        tunnel.assert_not_called()

        client, upstream = mock.Mock(), mock.Mock()
        upstream.sendall.side_effect = BrokenPipeError("gone")
        with (
            mock.patch.object(client_hello, "admit", return_value=b"hello"),
            mock.patch.object(app.Handler, "_tunnel") as tunnel,
        ):
            app.Handler._relay(client, upstream)
        upstream.settimeout.assert_called_once_with(app.CONNECT_TIMEOUT)
        for stream in (client, upstream):
            stream.close.assert_called_once_with()
        tunnel.assert_not_called()

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
