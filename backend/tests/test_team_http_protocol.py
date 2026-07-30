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
    "commit": "82ef5f9f56b2813e854716b10e6e731e70868cff",
    "path": "protocol/http/v1",
    "tree": "d5e10f7f3359bcb9b5399063680ee55b4cf4f3f2",
    "contract_files_sha256": "3cab716adcc58db6da1a743f78b552138adf26f65eb799046b6f34200a8fb315",
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
