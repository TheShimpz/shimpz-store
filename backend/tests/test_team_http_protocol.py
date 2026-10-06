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
    "commit": "812b1e7b5fb4b1c69c16d4c5d2c3459792a6de13",
    "path": "protocol/http/v1",
    "tree": "8a1e0c526587c37ad598f9145597236db75faec6",
    "contract_files_sha256": "3db39ef85285ce553b05a7253c8189da56e919aee31bdf1383b4c960f22ef3b2",
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
