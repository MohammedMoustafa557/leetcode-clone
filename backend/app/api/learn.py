"""Study plans, problem of the day, per-problem guide and the Learn section."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import DB, OptionalUser
from app.models import Problem
from app.services import clock, guide, plans
from app.services.content import load
from app.services.progress import status_map

router = APIRouter(tags=["learn"])


def _brief(p: Problem, statuses: dict[int, str]) -> dict:
    return {"slug": p.slug, "title": p.title, "difficulty": p.difficulty, "frontend_id": p.frontend_id,
            "status": statuses.get(p.id, "todo")}


@router.get("/plans")
def list_plans(db: DB, user: OptionalUser) -> list[dict]:
    out = []
    statuses = status_map(db, user.id) if user else {}
    for key, meta in plans.PLANS.items():
        groups, upstream = plans.plan_groups(db, key)
        ids = [p.id for _, ps in groups for p in ps]
        out.append({"id": key, **meta, "matched": len(ids), "upstream_total": upstream, "groups": len(groups),
                    "solved": sum(1 for i in ids if statuses.get(i) == "solved")})
    return out


@router.get("/plans/{plan_id}")
def get_plan(plan_id: str, db: DB, user: OptionalUser) -> dict:
    if plan_id not in plans.PLANS:
        raise HTTPException(404, "Unknown plan")
    groups, upstream = plans.plan_groups(db, plan_id)
    statuses = status_map(db, user.id) if user else {}
    return {
        "id": plan_id, **plans.PLANS[plan_id], "upstream_total": upstream,
        "matched": sum(len(ps) for _, ps in groups),
        "groups": [{"name": n, "problems": [_brief(p, statuses) for p in ps]} for n, ps in groups],
    }


@router.get("/daily")
def daily(db: DB, user: OptionalUser) -> dict:
    today = clock.now().date()
    p, group = plans.daily_pick(db, today)
    if p is None:
        raise HTTPException(404, "No problems loaded")
    statuses = status_map(db, user.id, [p.id]) if user else {}
    return {"date": today.isoformat(), "group": group, "problem": _brief(p, statuses)}


@router.get("/problems/{slug}/guide")
def problem_guide(slug: str, db: DB) -> dict:
    p = db.scalar(select(Problem).where(Problem.slug == slug))
    if p is None:
        raise HTTPException(404, "Problem not found")
    return guide.get_guide(db, p)


@router.get("/learn/patterns")
def patterns(db: DB) -> list[dict]:
    data = load("patterns.json")["patterns"]
    slugs = {s for pat in data for s in pat["slugs"]}
    found = {p.slug: p for p in db.scalars(select(Problem).where(Problem.slug.in_(slugs)))}
    return [{**{k: v for k, v in pat.items() if k != "slugs"},
             "problems": [_brief(found[s], {}) for s in pat["slugs"] if s in found]} for pat in data]


@router.get("/learn/sql")
def sql_questions() -> dict:
    return load("sql_qa.json")


@router.get("/learn/templates")
def templates() -> dict:
    return load("templates.json")


@router.get("/learn/behavioral")
def behavioral() -> dict:
    return load("behavioral.json")


@router.get("/learn/system-design")
def system_design() -> dict:
    return load("system_design.json")
