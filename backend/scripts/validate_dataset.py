"""Judge every problem's reference solution with the real harness (CPython).

    python -m scripts.validate_dataset [--timeout 20] [--workers 2]

Each problem runs in its own subprocess with a time and 1 GB memory cap; results are
appended to data/validation.jsonl (resumable). Problems that fail are written to
scripts/heavy_problems.json, which the seed script uses to flag heavy test suites.
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import json
import subprocess
import sys
from pathlib import Path

from scripts.seed import DATA_DIR, HEAVY_FILE, load_dataset

RUNNER = Path(__file__).resolve().parents[2] / "runner"
CHILD = f"""
import json, resource, sys
resource.setrlimit(resource.RLIMIT_AS, (1 << 30, 1 << 30))
sys.path.insert(0, {str(RUNNER)!r})
import harness
r = json.loads(sys.stdin.read())
res = harness.run(r["prompt"], r["completion"], r["entry_point"], r["test"])
print("RESULT" + json.dumps([res["verdict"], res["passed"], res["total"]]))
"""


def judge_one(row: dict, timeout: int) -> list:
    try:
        proc = subprocess.run(
            [sys.executable, "-c", CHILD], input=json.dumps(row), capture_output=True, text=True, timeout=timeout
        )
        line = next((ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT")), None)
        return [row["task_id"], *json.loads(line[6:])] if line else [row["task_id"], "Crash", 0, 0]
    except subprocess.TimeoutExpired:
        return [row["task_id"], "Time Limit Exceeded", 0, 0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()

    rows = load_dataset(DATA_DIR)
    out = DATA_DIR / "validation.jsonl"
    done = {json.loads(line)[0] for line in out.open()} if out.exists() else set()
    todo = [r for r in rows if r["task_id"] not in done]
    print(f"{len(done)} already judged, {len(todo)} to go")
    with out.open("a") as fh, cf.ThreadPoolExecutor(args.workers) as pool:
        for i, res in enumerate(pool.map(lambda r: judge_one(r, args.timeout), todo), 1):
            fh.write(json.dumps(res) + "\n")
            fh.flush()
            if i % 100 == 0:
                print(f"  {i}/{len(todo)}")

    results = [json.loads(line) for line in out.open()]
    counts = collections.Counter(r[1] for r in results)
    print(dict(counts))
    heavy = sorted(r[0] for r in results if r[1] != "Accepted")
    data = json.loads(HEAVY_FILE.read_text()) if HEAVY_FILE.exists() else {}
    data["slugs"] = heavy
    HEAVY_FILE.write_text(json.dumps(data, indent=1) + "\n")
    print(f"{len(heavy)} problems flagged in {HEAVY_FILE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
