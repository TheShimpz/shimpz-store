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
    "commit": "c8af57df71ad74ad55d752766103502cb580ae95",
    "path": "protocol/http/v1",
    "tree": "4a8c265734d97331400a663ab536aa68da5e1369",
    "contract_files_sha256": "f2b3deff6990b88616c59370878b1eee27591550eceeefb23c87752bdfa59ef3",
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
