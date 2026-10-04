"""Pin and execute the generated Team HTTP protocol mirror."""

from __future__ import annotations

import hashlib
import json
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app" / "protocol" / "http"
DEPENDENCIES = ("payload", "progress", "supervisor", "websocket")
EXPECTED_UPSTREAM = {
    "repository": "https://github.com/TheShimpz/shimpz-teams",
    "commit": "09c6fa1d70dcb858038f163617c2c3a766e133aa",
    "path": "protocol/http/v1",
    "tree": "abae31905af076fc06767fe1cb979a41d76b7242",
    "contract_files_sha256": "17015bc2ac021ec5af354a2ddecfe75ff1367518cdf045da02a727d7c1d30347",
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
