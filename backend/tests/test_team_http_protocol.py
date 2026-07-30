"""Pin and execute the generated Team HTTP protocol mirror."""

from __future__ import annotations

import hashlib
import json
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app" / "protocol" / "http"
EXPECTED_UPSTREAM = {
    "repository": "https://github.com/TheShimpz/shimpz-teams",
    "commit": "870622b2c82ed6f45f6579c623d884709bf2e8de",
    "path": "protocol/http/v1",
    "tree": "896c7062358d2bf8fa276934c5c71f4f026721b3",
    "contract_files_sha256": "414040157418f6090b13e7265ec74c645a7a5357a32cc4953c00186390bb6580",
}


def test_mirror_matches_pin_and_vectors() -> None:
    assert json.loads((ROOT / "upstream.json").read_bytes()) == EXPECTED_UPSTREAM
    manifest = (ROOT / "v1" / "contract-files.sha256").read_bytes()
    assert (
        hashlib.sha256(manifest).hexdigest()
        == EXPECTED_UPSTREAM["contract_files_sha256"]
    )
    protocol_root = str(ROOT / "v1")
    sys.path.insert(0, protocol_root)
    try:
        runpy.run_path(str(ROOT / "v1" / "verify.py"), run_name="__main__")
    finally:
        sys.path.remove(protocol_root)
