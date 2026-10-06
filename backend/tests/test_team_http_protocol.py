"""Pin and execute the generated Team HTTP protocol mirror."""

from __future__ import annotations

import hashlib
import json
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app" / "protocol" / "http"
DEPENDENCIES = ("identifiers", "payload", "progress", "purpose", "strict_json", "supervisor", "turn", "websocket")
EXPECTED_UPSTREAM = {
    "repository": "https://github.com/TheShimpz/shimpz-teams",
    "commit": "1e1c3d8465a2a7c449a1070f69fe735f68c23c4e",
    "path": "protocol/http/v1",
    "tree": "6c000cde0601ea8cbf1d73f8e3129e09344f173e",
    "contract_files_sha256": "f8d7ec18aa2bd57b2ca23fbb89fd193bc99fc885cf1be27e60eb25be1a2abaf8",
}


def test_mirror_matches_pin_and_vectors() -> None:
    assert json.loads((ROOT / "upstream.json").read_bytes()) == EXPECTED_UPSTREAM
    manifest = (ROOT / "v1" / "contract-files.sha256").read_bytes()
    assert hashlib.sha256(manifest).hexdigest() == EXPECTED_UPSTREAM["contract_files_sha256"]
    protocol_root = str(ROOT / "v1")
    saved = {name: sys.modules.pop(name, None) for name in DEPENDENCIES}
    sys.path.insert(0, protocol_root)
    try:
        runpy.run_path(str(ROOT / "v1" / "verify.py"), run_name="__main__")
    finally:
        sys.path.remove(protocol_root)
        for name in DEPENDENCIES:
            sys.modules.pop(name, None)
            if saved[name] is not None:
                sys.modules[name] = saved[name]
