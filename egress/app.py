#!/usr/local/bin/python3
"""CONNECT-only outbound enforcement from hosted Store to private Neuron."""

from __future__ import annotations

import contextlib
import ipaddress
import select
import socket
import socketserver
import threading

import audit

LISTEN_PORT = 8889
ALLOWED_HOST = "neuron.shimpz.com"
ALLOWED_PORT = 443
CONNECT_TIMEOUT = 10
IDLE_TIMEOUT = 30
BUFFER_SIZE = 64 * 1024
MAX_REQUEST_BYTES = 1024
MAX_CONCURRENCY = 8
MAX_SOURCE_CONCURRENCY = 8
LISTEN_BACKLOG = 8
EXACT_REQUEST = b"CONNECT neuron.shimpz.com:443 HTTP/1.1\r\nHost: neuron.shimpz.com:443\r\n\r\n"
_STATUS = {
    200: "Connection established",
    400: "Bad Request",
    403: "Forbidden",
    502: "Bad Gateway",
    503: "Service Unavailable",
}
_AUDIT_SUBJECTS = {
    "allowed": "neuron.shimpz.com:443",
    "upstream-unavailable": "neuron.shimpz.com:443",
    "request-rejected": "rejected-target",
    "destination-rejected": "rejected-target",
}


def resolve_public(host: str, port: int) -> tuple[int, tuple] | None:
    """Return one already-validated public address, rejecting mixed answers."""
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError:
        return None
    public: list[tuple[int, tuple]] = []
    for family, _kind, _protocol, _canonical, address in addresses:
        try:
            parsed = ipaddress.ip_address(address[0])
        except ValueError:
            return None
        if not parsed.is_global:
            return None
        public.append((family, address))
    return public[0] if public else None


def _read_request(stream: socket.socket) -> bytes | None:
    payload = bytearray()
    while b"\r\n\r\n" not in payload:
        try:
            chunk = stream.recv(256)
        except OSError:
            return None
        if not chunk:
            return None
        payload.extend(chunk)
        if len(payload) > MAX_REQUEST_BYTES:
            return None
    return bytes(payload)


def _admit(request: bytes | None) -> tuple[int, str, tuple[int, tuple] | None]:
    if request is None:
        return 0, "incomplete", None
    if request != EXACT_REQUEST:
        return 400, "request-rejected", None
    resolved = resolve_public(ALLOWED_HOST, ALLOWED_PORT)
    if resolved is None:
        return 403, "destination-rejected", None
    return 200, "allowed", resolved


class Handler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        client = self.request
        client.settimeout(CONNECT_TIMEOUT)
        code, reason, resolved = _admit(_read_request(client))
        if resolved is None:
            if code:
                self._deny(client, code, reason)
            return
        self._connect(client, resolved)

    @staticmethod
    def _reply(client: socket.socket, code: int) -> None:
        with contextlib.suppress(OSError):
            client.sendall(f"HTTP/1.1 {code} {_STATUS[code]}\r\n\r\n".encode("ascii"))

    @classmethod
    def _deny(cls, client: socket.socket, code: int, reason: str) -> None:
        try:
            audit.record(
                result="error" if code >= 500 else "denied",
                code=code,
                reason=reason,
                subject=_AUDIT_SUBJECTS[reason],
            )
        except audit.AuditError:
            code = 503
        cls._reply(client, code)

    @classmethod
    def _connect(cls, client: socket.socket, resolved: tuple[int, tuple]) -> None:
        upstream = _connect_upstream(resolved)
        if upstream is None:
            cls._deny(client, 502, "upstream-unavailable")
            return
        try:
            audit.record(
                result="ok",
                code=200,
                reason="allowed",
                subject="neuron.shimpz.com:443",
            )
        except audit.AuditError:
            upstream.close()
            cls._reply(client, 503)
            return
        cls._reply(client, 200)
        cls._tunnel(client, upstream)

    @staticmethod
    def _tunnel(first: socket.socket, second: socket.socket) -> None:
        for stream in (first, second):
            stream.settimeout(IDLE_TIMEOUT)
        try:
            while True:
                readable, _, errored = select.select([first, second], [], [first, second], IDLE_TIMEOUT)
                if errored or not readable:
                    return
                for source in readable:
                    payload = source.recv(BUFFER_SIZE)
                    if not payload:
                        return
                    (second if source is first else first).sendall(payload)
        except OSError:
            return
        finally:
            for stream in (first, second):
                with contextlib.suppress(OSError):
                    stream.shutdown(socket.SHUT_RDWR)
                stream.close()


def _connect_upstream(resolved: tuple[int, tuple]) -> socket.socket | None:
    family, address = resolved
    upstream: socket.socket | None = None
    try:
        upstream = socket.socket(family, socket.SOCK_STREAM)
        upstream.settimeout(CONNECT_TIMEOUT)
        upstream.connect(address)
    except OSError:
        if upstream is not None:
            upstream.close()
        return None
    return upstream


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = LISTEN_BACKLOG

    def __init__(self, *args, **kwargs) -> None:
        self._slots = threading.BoundedSemaphore(MAX_CONCURRENCY)
        self._source_guard = threading.Lock()
        self._source_counts: dict[str, int] = {}
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address) -> None:
        source = client_address[0]
        saturated = False
        with self._source_guard:
            source_count = self._source_counts.get(source, 0)
            if source_count >= MAX_SOURCE_CONCURRENCY or not self._slots.acquire(blocking=False):
                saturated = True
            else:
                self._source_counts[source] = source_count + 1
        if saturated:
            request.settimeout(CONNECT_TIMEOUT)
            with contextlib.suppress(audit.AuditError):
                audit.record(
                    result="denied",
                    code=503,
                    reason="capacity",
                    subject="not-evaluated",
                )
            Handler._reply(request, 503)
            request.close()
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._release(source)
            raise

    def process_request_thread(self, request, client_address) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._release(client_address[0])

    def _release(self, source: str) -> None:
        with self._source_guard:
            remaining = self._source_counts[source] - 1
            if remaining:
                self._source_counts[source] = remaining
            else:
                del self._source_counts[source]
        self._slots.release()


def main() -> int:
    try:
        audit.ensure_custody()
        server = Server((str(ipaddress.IPv4Address(0)), LISTEN_PORT), Handler)
    except audit.AuditError, OSError:
        return 1
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
