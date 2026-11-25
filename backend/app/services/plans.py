"""Study plans (Blind 75, NeetCode roadmap, Striver SDE) and the problem of the day."""

from __future__ import annotations

import hashlib
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Problem
from app.services.content import load

# NeetCode's own roadmap order.
NEETCODE_ORDER = [
    "Arrays & Hashing", "Two Pointers", "Sliding Window", "Stack", "Binary Search", "Linked List", "Trees",
    "Heap / Priority Queue", "Backtracking", "Tries", "Graphs", "Advanced Graphs", "1-D Dynamic Programming",
    "2-D Dynamic Programming", "Greedy", "Intervals", "Math & Geometry", "Bit Manipulation", "JavaScript",
]

PLANS = {
    "blind75": {"title": "Blind 75", "description": "The classic 75 must-know problems, grouped by topic in NeetCode order."},
    "neetcode": {"title": "NeetCode Roadmap", "description": "NeetCode's full roadmap (NeetCode 150 + extras), by topic."},
    "striver": {"title": "Striver SDE Sheet", "description": "Day-by-day topic sheet inspired by Striver's SDE Sheet."},
}


def _raw_groups(plan: str) -> list[tuple[str, list[str]]]:
    if plan == "striver":
        return [(g["name"], g["slugs"]) for g in load("striver_sde.json")["groups"]]
    rows = load("neetcode.json")["problems"]
    if plan == "blind75":
        rows = [r for r in rows if r["blind75"]]
    groups: dict[str, list[str]] = {}
    for r in rows:
        groups.setdefault(r["pattern"], []).append(r["slug"])
    return [(name, groups[name]) for name in NEETCODE_ORDER if name in groups]


def plan_groups(db: Session, plan: str) -> tuple[list[tuple[str, list[Problem]]], int]:
    """Groups with only problems that exist in our catalog, plus the upstream total."""
    raw = _raw_groups(plan)
    wanted = {s for _, slugs in raw for s in slugs}
    found = {p.slug: p for p in db.scalars(select(Problem).where(Problem.slug.in_(wanted)))} if wanted else {}
    out = []
    for name, slugs in raw:
        seen: list[Problem] = []
        for s in slugs:
            if s in found and found[s] not in seen:
                seen.append(found[s])
        if seen:
            out.append((name, seen))
    return out, sum(len(s) for _, s in raw)


def _h(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest(), 16)


def daily_pick(db: Session, day: date) -> tuple[Problem | None, str | None]:
    """Deterministic problem of the day: rotate through NeetCode groups, then pick inside the group."""
    groups, _ = plan_groups(db, "neetcode")
    groups = [(n, [p for p in ps if not p.heavy_tests and p.difficulty != "Hard"]) for n, ps in groups]
    groups = [(n, ps) for n, ps in groups if ps]
    if groups:
        name, problems = groups[day.toordinal() % len(groups)]
        return problems[_h(day.isoformat()) % len(problems)], name
    pool = list(db.scalars(select(Problem).where(Problem.heavy_tests.is_(False)).order_by(Problem.id)))
    if not pool:
        return None, None
    return pool[_h(day.isoformat()) % len(pool)], None
