"""Compare the Rust Store with the Python Store's functions on seeded cases (tooling until the Python is deleted).

Run once with the Store's own Python environment, from the umbrella root:

    uv run --project store/backend --frozen python store/backend/oracle/differential.py --count 1000000

For each domain it draws `--count` cases from `--seed`, decides each with the Python `app.*` functions in a process
pool sized by the gate's worker budget, runs the release `decide` example once over all of them, and exits non-zero
on any disagreement it prints. With `--corpus`, every case whose Python decision reached a line of `app/` no earlier
case reached is written, with its decision, to `tests/corpus/<domain>.json`, where `tests/corpus.rs` replays it.
"""

import argparse
import json
import os
import random
import struct
import subprocess
import sys
import tempfile
import urllib.parse
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cases
import decide

ROOT = Path(__file__).resolve().parent.parent
APP = str(ROOT / "app")
# The query domain's Python is the standard library parser the Store's routes called; its lines count as reached too.
PARSER = urllib.parse.__file__
SHOWN = 5
_WORK: list[Path] = []
_REACHED: list[bool] = []


def workers() -> int:
    """SHIMPZ_TEST_WORKERS when set, else half of this process's processors."""
    configured = os.environ.get("SHIMPZ_TEST_WORKERS", "")
    if configured:
        return int(configured)
    return max(1, (os.process_cpu_count() or 2) // 2)


def _on_line(code, _line):
    if code.co_filename.startswith(APP) or code.co_filename == PARSER:
        _REACHED[0] = True
    return sys.monitoring.DISABLE


def _start_worker(work: str) -> None:
    decide.prepare(Path(work))
    _REACHED.append(False)
    tool = sys.monitoring.COVERAGE_ID
    sys.monitoring.use_tool_id(tool, "store-differential")
    sys.monitoring.register_callback(tool, sys.monitoring.events.LINE, _on_line)
    sys.monitoring.set_events(tool, sys.monitoring.events.LINE)


def _decide_chunk(chunk: list[dict]) -> list[tuple[str, bool]]:
    answers = []
    for case in chunk:
        _REACHED[0] = False
        answers.append((decide.decide(case), _REACHED[0]))
    return answers


def python_answers(drawn: list[dict], work: Path, jobs: int) -> list[tuple[str, bool]]:
    chunk = max(1, len(drawn) // (jobs * 16))
    chunks = [drawn[start : start + chunk] for start in range(0, len(drawn), chunk)]
    with ProcessPoolExecutor(max_workers=jobs, initializer=_start_worker, initargs=(str(work),)) as pool:
        return [answer for answers in pool.map(_decide_chunk, chunks) for answer in answers]


def rust_answers(drawn: list[dict], work: Path, jobs: int) -> list[str]:
    framed = b"".join(
        struct.pack(">I", len(encoded)) + encoded
        for encoded in (json.dumps(case, ensure_ascii=False).encode() for case in drawn)
    )
    completed = subprocess.run(
        ["cargo", "run", "--quiet", "--release", "--locked", "--jobs", str(jobs), "--example", "decide", str(work)],
        cwd=ROOT,
        input=framed,
        capture_output=True,
        check=True,
    )
    return completed.stdout.decode().split("\n")[:-1]


def compare(domain: str, drawn: list[dict], python: list[tuple[str, bool]], rust: list[str]) -> int:
    if len(rust) != len(python):
        print(f"{domain}: decide wrote {len(rust)} lines for {len(python)} cases", file=sys.stderr)
        return 1
    mismatches = [index for index in range(len(drawn)) if python[index][0] != rust[index]]
    for index in mismatches[:SHOWN]:
        print(f"{domain} case {json.dumps(drawn[index])[:600]}", file=sys.stderr)
        print(f"  python {python[index][0][:300]!r}\n  rust   {rust[index][:300]!r}", file=sys.stderr)
    refused = sum(answer[0] in {"refuse", '["refuse",null]'} for answer in python)
    print(f"{domain}: {len(drawn)} cases, {refused} refused, {len(mismatches)} disagreements", flush=True)
    return len(mismatches)


def write_corpus(domain: str, drawn: list[dict], python: list[tuple[str, bool]]) -> None:
    kept = [{"case": case, "python": answer} for case, (answer, reached) in zip(drawn, python, strict=True) if reached]
    path = ROOT / "tests" / "corpus" / f"{domain}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(kept, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")


def run_domain(domain: str, arguments, work: Path, jobs: int) -> int:
    rng = random.Random(f"{arguments.seed}-{domain}")
    decide.prepare(work)
    drawn = [decide.materialize(cases.GENERATORS[domain](rng)) for _ in range(arguments.count)]
    python = python_answers(drawn, work, jobs)
    disagreements = compare(domain, drawn, python, rust_answers(drawn, work, jobs))
    if arguments.corpus and not disagreements:
        write_corpus(domain, drawn, python)
    return disagreements


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--domain", action="append", choices=sorted(cases.GENERATORS))
    parser.add_argument("--corpus", action="store_true")
    arguments = parser.parse_args()
    jobs = workers()
    if arguments.corpus:
        tree = [list(entry) for entry in decide.TREE]
        (ROOT / "tests" / "corpus").mkdir(parents=True, exist_ok=True)
        (ROOT / "tests" / "corpus" / "tree.json").write_text(json.dumps(tree, ensure_ascii=False) + "\n", "utf-8")
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        failed = sum(run_domain(domain, arguments, work, jobs) for domain in arguments.domain or cases.GENERATORS)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
