"""Pin and execute the generated Team HTTP protocol mirror."""

from __future__ import annotations

import hashlib
import json
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app" / "protocol" / "http"
DEPENDENCIES = ("identifiers", "payload", "progress", "purpose", "strict_json", "supervisor", "websocket")
EXPECTED_UPSTREAM = {
    "repository": "https://github.com/TheShimpz/shimpz-teams",
    "commit": "3002178e8897ec7b16deecd51c90b357b02b6047",
    "path": "protocol/http/v1",
    "tree": "71738be3678d48670c021b12bac02e9c5c086135",
    "contract_files_sha256": "de8ed0779a9486f62933a8c0ff4eb7e729b258b9675686d0ecd075523e2d02f6",
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
