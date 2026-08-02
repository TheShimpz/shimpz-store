#!/usr/local/bin/python3
"""Prove that the Store CONNECT boundary is accepting local connections."""

from __future__ import annotations

import socket


def main() -> int:
    try:
        with socket.create_connection(("127.0.0.1", 8889), timeout=2):
            pass
    except OSError:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
