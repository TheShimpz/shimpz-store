#!/usr/local/bin/python3
"""CONNECT-only outbound enforcement from hosted Store to private Neuron.

The image's neutral CONNECT transport (`connect`, ADR-0104) resolves, records, connects, admits the TLS ClientHello,
and splices; this profile owns only its exact request, audit, and resource envelope.
"""

import ipaddress

import audit
import connect

LISTEN_PORT = 8889
ALLOWED_HOST = "neuron.shimpz.com"
ALLOWED_PORT = 443
MAX_CONCURRENCY = 8
MAX_SOURCE_CONCURRENCY = 8
LISTEN_BACKLOG = 8
EXACT_REQUEST = b"CONNECT neuron.shimpz.com:443 HTTP/1.1\r\nHost: neuron.shimpz.com:443\r\n\r\n"


class Handler(connect.ConnectHandler):
    connect_timeout = 10
    idle_timeout = 30
    request_limit = 1024

    def admit(self, request: bytes) -> connect.Target | connect.Decision:
        """Network-gated: admit only the one exact Neuron request."""
        if request != EXACT_REQUEST:
            return connect.refuse(400, "request-rejected", "rejected-target")
        return connect.Target(ALLOWED_HOST, ALLOWED_PORT)

    @classmethod
    def record(cls, decision: connect.Decision) -> None:
        audit.record(decision)


class Server(connect.BoundedServer):
    max_concurrency = MAX_CONCURRENCY
    max_source_concurrency = MAX_SOURCE_CONCURRENCY
    request_queue_size = LISTEN_BACKLOG


def main() -> int:
    try:
        audit.AUDIT.ensure_custody()
        server = Server((str(ipaddress.IPv4Address(0)), LISTEN_PORT), Handler)
    except OSError:
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
