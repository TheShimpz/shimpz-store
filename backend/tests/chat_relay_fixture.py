"""Loopback Team chat stream driver shared by relay suites."""

import contextlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app import config


@contextlib.contextmanager
def real_stream_driver(response_body: bytes, *, status: int = 200):
    requests: list[bytes] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            requests.append(self.rfile.read(length))
            self.send_response(status)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)

        def log_message(self, *_args) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(
        target=server.serve_forever,
        kwargs={"poll_interval": 0.01},
        daemon=True,
    )
    worker.start()
    previous = config.TEAMDRIVER_URL
    config.TEAMDRIVER_URL = f"http://127.0.0.1:{server.server_port}"
    try:
        yield requests
    finally:
        config.TEAMDRIVER_URL = previous
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
