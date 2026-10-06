"""One loopback HTTP peer that Store suites stand in for Team, Account, or Brain."""

import contextlib
import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


@contextlib.contextmanager
def loopback_server(handler: type[BaseHTTPRequestHandler]) -> Iterator[int]:
    """Serve handler on an ephemeral loopback port for the block, then stop and join it."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    worker = threading.Thread(
        target=server.serve_forever,
        kwargs={"poll_interval": 0.01},
        daemon=True,
    )
    worker.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


class PeerMixin:
    """Quiet logging plus JSON response and request-body helpers for a loopback peer's request handler."""

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def log_message(self, *_args) -> None:
        pass
