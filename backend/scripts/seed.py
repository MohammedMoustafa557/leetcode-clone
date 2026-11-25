"""Download the public datasets and load them into the database.

    python -m scripts.seed                 # download (cached) + load everything
    python -m scripts.seed --limit 50      # quick dev seed
    python -m scripts.seed --skip-companies

Sources (downloaded at setup time, never committed to git):
  * LeetCodeDataset (Apache-2.0) - https://huggingface.co/datasets/newfacade/LeetCodeDataset
  * leetcode-company-wise-problems (community-collected company tags, no license
    file, so we only download it locally) - https://github.com/liquidslr/leetcode-company-wise-problems
"""

from __future__ import annotations

import argparse
import ast
import csv
import io
import json
import re
import sys
import tarfile
import time
import urllib.request
import warnings
from datetime import date
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db import Base, SessionLocal, engine
from app.models import Company, Problem, ProblemCompany, Tag, problem_tags

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HEAVY_FILE = Path(__file__).resolve().parent / "heavy_problems.json"
HF_BASE = "https://huggingface.co/datasets/newfacade/LeetCodeDataset/resolve/main/"
DATASET_FILES = ["LeetCodeDataset-train.jsonl", "LeetCodeDataset-test.jsonl"]
COMPANY_TARBALL = (
    "https://codeload.github.com/liquidslr/leetcode-company-wise-problems/tar.gz/refs/heads/main"
)
# file name -> recency bucket (most recent first)
RECENCY_FILES = [
    ("1. Thirty Days.csv", "30d"),
    ("2. Three Months.csv", "3m"),
    ("3. Six Months.csv", "6m"),
    ("4. More Than Six Months.csv", "6m+"),
]
SMALL_WORDS = {
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of", "on", "or", "the", "to", "vs", "with",
}
ROMAN = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}


def log(msg: str) -> None:
    print(f"[seed] {msg}", flush=True)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def title_from_slug(slug: str) -> str:
    words = slug.split("-")
    out = []
    for i, w in enumerate(words):
        if w in ROMAN:
            out.append(w.upper())
        elif i and w in SMALL_WORDS:
            out.append(w)
        else:
            out.append(w[:1].upper() + w[1:])
    return " ".join(out)


def download(url: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    log(f"downloading {url}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "codearena-seed/1.0"})
    with urllib.request.urlopen(req, timeout=300) as resp, open(tmp, "wb") as fh:
        while chunk := resp.read(1 << 20):
            fh.write(chunk)
    tmp.rename(dest)
    return dest


def load_dataset(data_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for name in DATASET_FILES:
        path = download(HF_BASE + name, data_dir / "leetcodedataset" / name)
        with open(path, encoding="utf-8") as fh:
            rows.extend(json.loads(line) for line in fh if line.strip())
    return rows


def load_company_csvs(data_dir: Path) -> dict[str, dict[str, tuple[float, str, str]]]:
    """company name -> {slug: (frequency, recency, title)}"""
    tar_path = download(COMPANY_TARBALL, data_dir / "company-wise" / "company-wise.tar.gz")
    result: dict[str, dict[str, tuple[float, str, str]]] = {}
    with tarfile.open(tar_path) as tar:
        files: dict[tuple[str, str], bytes] = {}
        for member in tar.getmembers():
            parts = member.name.split("/")
            if member.isfile() and len(parts) == 3 and parts[2].endswith(".csv"):
                files[(parts[1], parts[2])] = tar.extractfile(member).read()
    companies = sorted({c for c, _ in files})
    for company in companies:
        all_csv = files.get((company, "5. All.csv"))
        if not all_csv:
            continue
        recency: dict[str, str] = {}
        for fname, bucket in reversed(RECENCY_FILES):  # oldest first, newer overwrite
            raw = files.get((company, fname))
            if raw:
                for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
                    recency[_slug_from_link(row.get("Link", ""))] = bucket
        entries = {}
        for row in csv.DictReader(io.StringIO(all_csv.decode("utf-8-sig"))):
            slug = _slug_from_link(row.get("Link", ""))
            if not slug:
                continue
            try:
                freq = float(row.get("Frequency") or 0)
            except ValueError:
                freq = 0.0
            entries[slug] = (freq, recency.get(slug, "6m+"), row.get("Title", "").strip())
        if entries:
            result[company] = entries
    return result


def _slug_from_link(link: str) -> str:
    link = link.strip().rstrip("/")
    return link.split("/problems/")[-1] if "/problems/" in link else ""


def count_cases(test_code: str) -> int:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        tree = ast.parse(test_code)
    check = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "check")
    return sum(isinstance(n, ast.Assert) for n in check.body)


def clean_description(text: str) -> str:
    text = text.replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def seed(db: Session, rows: list[dict], companies: dict | None) -> dict:
    db.execute(delete(ProblemCompany))
    db.execute(delete(problem_tags))
    db.execute(delete(Company))
    db.execute(delete(Tag))
    # keep problem ids stable across re-seeds so user submissions survive
    existing = {p.slug: p for p in db.scalars(select(Problem))}

    titles: dict[str, str] = {}
    for entries in (companies or {}).values():
        for slug, (_, _, title) in entries.items():
            if title:
                titles.setdefault(slug, title)

    heavy = set(json.loads(HEAVY_FILE.read_text())["slugs"]) if HEAVY_FILE.exists() else set()
    tags: dict[str, Tag] = {}
    by_slug: dict[str, Problem] = {}
    for r in sorted(rows, key=lambda r: r["question_id"]):
        slug = r["task_id"]
        p = existing.get(slug) or Problem(slug=slug)
        p.frontend_id = int(r["question_id"])
        p.title = titles.get(slug) or title_from_slug(slug)
        p.difficulty = r["difficulty"]
        p.description = clean_description(r["problem_description"])
        p.starter_code = r["starter_code"].rstrip() + "\n        "
        p.entry_point = r["entry_point"]
        p.preamble = r["prompt"]
        p.test_code = r["test"]
        p.test_count = count_cases(r["test"])
        p.solution = r.get("completion") or ""
        p.heavy_tests = slug in heavy
        try:
            p.released = date.fromisoformat(r.get("estimated_date") or "")
        except ValueError:
            p.released = None
        p.tags = []
        for name in r.get("tags") or []:
            if name not in tags:
                tags[name] = Tag(name=name, slug=slugify(name))
                db.add(tags[name])
            p.tags.append(tags[name])
        db.add(p)
        by_slug[slug] = p
    db.flush()

    linked = 0
    tagged: set[str] = set()
    for name, entries in (companies or {}).items():
        company = Company(name=name, slug=slugify(name))
        db.add(company)
        db.flush()
        for slug, (freq, recency, _) in entries.items():
            p = by_slug.get(slug)
            if p is None:
                continue
            db.add(ProblemCompany(problem_id=p.id, company_id=company.id, frequency=freq, recency=recency))
            linked += 1
            tagged.add(slug)
    db.commit()
    return {
        "problems": len(by_slug),
        "tags": len(tags),
        "companies": len(companies or {}),
        "problem_company_links": linked,
        "problems_with_company_tags": len(tagged),
        "heavy_test_suites": sum(p.heavy_tests for p in by_slug.values()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--limit", type=int, default=None, help="only load the first N problems")
    parser.add_argument("--skip-companies", action="store_true")
    parser.add_argument("--create-tables", action="store_true", help="create tables without Alembic (dev/tests)")
    parser.add_argument("--if-empty", action="store_true", help="do nothing when problems are already loaded")
    args = parser.parse_args(argv)

    started = time.time()
    if args.create_tables:
        Base.metadata.create_all(engine)
    if args.if_empty:
        with SessionLocal() as db:
            if db.scalar(select(func.count(Problem.id))):
                log("problems already loaded, skipping (drop --if-empty to re-seed)")
                return 0
    rows = load_dataset(args.data_dir)
    if args.limit:
        rows = sorted(rows, key=lambda r: r["question_id"])[: args.limit]
    companies = None if args.skip_companies else load_company_csvs(args.data_dir)
    with SessionLocal() as db:
        stats = seed(db, rows, companies)
    log(json.dumps(stats))
    log(f"done in {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
