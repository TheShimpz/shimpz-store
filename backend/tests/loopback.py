"""One loopback HTTP peer that Store suites stand in for Team, Account, or Brain."""

import contextlib
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
