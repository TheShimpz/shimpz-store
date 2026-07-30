"""Pin and execute the generated Team HTTP protocol mirror."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app" / "protocol" / "http"
EXPECTED_UPSTREAM = {
    "repository": "https://github.com/TheShimpz/shimpz-teams",
    "commit": "852caaf538ce89e85f81c6909f2250ff2bbb0ed5",
    "path": "protocol/http/v1",
    "tree": "d5e10f7f3359bcb9b5399063680ee55b4cf4f3f2",
    "contract_files_sha256": "3cab716adcc58db6da1a743f78b552138adf26f65eb799046b6f34200a8fb315",
}


def test_mirror_matches_pin_and_vectors() -> None:
    assert json.loads((ROOT / "upstream.json").read_bytes()) == EXPECTED_UPSTREAM
    manifest = (ROOT / "v1" / "contract-files.sha256").read_bytes()
    assert hashlib.sha256(manifest).hexdigest() == EXPECTED_UPSTREAM["contract_files_sha256"]
    subprocess.run([sys.executable, str(ROOT / "v1" / "verify.py")], check=True)
