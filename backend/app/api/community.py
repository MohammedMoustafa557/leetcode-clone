"""Public profiles/dashboard, leaderboard and weekly contests."""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import DB, CurrentUser, OptionalUser
from app.models import Contest, ContestEntry, Problem, User
from app.services import clock
from app.services import community as svc

router = APIRouter(tags=["community"])


def _profile(db, u: User) -> dict:
    s = svc.summarize(db, u)
    totals = {d: db.query(Problem).filter(Problem.difficulty == d).count() for d in ("Easy", "Medium", "Hard")}
    return {
        "username": u.username, "joined": u.created_at.isoformat(),
        "solved": s.solved, "totals": totals, "points": s.points, "streak": s.streak, "max_streak": s.max_streak,
        "rating": u.rating, "global_rank": svc.global_rank(db, u), "contests": s.contests,
        "badges": svc.badges(db, s),
        "contest_history": [
            {"number": c.number, "title": c.title, "rank": e.rank, "rating_before": e.rating_before,
             "rating_after": e.rating_after, "score": e.score}
            for e, c in db.execute(select(ContestEntry, Contest).join(Contest)
                                   .where(ContestEntry.user_id == u.id, ContestEntry.rating_after.is_not(None))
                                   .order_by(Contest.number))
        ],
    }


@router.get("/users/{username}")
def public_profile(username: str, db: DB) -> dict:
    u = db.scalar(select(User).where(User.username == username))
    if u is None:
        raise HTTPException(404, "User not found")
    return _profile(db, u)


@router.get("/leaderboard")
def leaderboard(
    db: DB,
    sort: Literal["points", "streak", "rating"] = "points",
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[dict]:
    rows = []
    for u in db.scalars(select(User)):
        s = svc.summarize(db, u)
        rows.append({"username": u.username, "points": s.points, "solved": sum(s.solved.values()),
                     "streak": s.streak, "max_streak": s.max_streak, "rating": u.rating})
    key = {"points": lambda r: (-r["points"], -r["streak"]), "streak": lambda r: (-r["streak"], -r["points"]),
           "rating": lambda r: (-r["rating"], -r["points"])}[sort]
    rows.sort(key=lambda r: (*key(r), r["username"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows[:limit]


def _contest_out(db, c: Contest, user: User | None) -> dict:
    svc.finalize_if_over(db, c)
    now = clock.now()
    start, end = clock.aware(c.starts_at), clock.aware(c.ends_at)
    phase = "upcoming" if now < start else "running" if now < end else "finished"
    ids = svc.contest_problem_ids(c)
    problems = {p.id: p for p in db.scalars(select(Problem).where(Problem.id.in_(ids)))}
    show = phase != "upcoming"
    entries = svc.standings(db, c)
    me = next((e for e in entries if user and e.user_id == user.id), None)
    my_results = {r["problem_id"]: r for r in svc.score_entry(db, c, user.id)[2]} if me else {}
    return {
        "number": c.number, "title": c.title, "starts_at": start.isoformat(), "ends_at": end.isoformat(),
        "phase": phase, "rated": c.rated, "registered": me is not None, "participants": len(entries),
        "problems": [
            {"index": i + 1, "points": svc.CONTEST_POINTS[i], "slug": problems[pid].slug,
             "title": problems[pid].title, "difficulty": problems[pid].difficulty,
             "solved": bool(my_results.get(pid, {}).get("solved"))}
            for i, pid in enumerate(ids) if pid in problems
        ] if show else [],
        "standings": [
            {"rank": e.rank or i + 1, "username": e.user.username, "score": e.score,
             "penalty_seconds": e.penalty_seconds, "rating_before": e.rating_before, "rating_after": e.rating_after}
            for i, e in enumerate(entries)
        ] if show else [],
    }


@router.get("/contests/current")
def current_contest(db: DB, user: OptionalUser) -> dict:
    c = svc.get_or_create_contest(db, svc.contest_number_at(clock.now()))
    return _contest_out(db, c, user)


@router.get("/contests")
def past_contests(db: DB) -> list[dict]:
    rows = db.scalars(select(Contest).order_by(Contest.number.desc()).limit(50))
    return [{"number": c.number, "title": c.title, "starts_at": clock.aware(c.starts_at).isoformat(),
             "rated": c.rated} for c in rows]


@router.get("/contests/{number}")
def get_contest(number: int, db: DB, user: OptionalUser) -> dict:
    c = db.scalar(select(Contest).where(Contest.number == number))
    if c is None:
        raise HTTPException(404, "Contest not found")
    return _contest_out(db, c, user)


@router.post("/contests/{number}/register", status_code=status.HTTP_201_CREATED)
def register(number: int, db: DB, user: CurrentUser) -> dict:
    c = db.scalar(select(Contest).where(Contest.number == number))
    if c is None:
        current = svc.contest_number_at(clock.now())
        if number not in (current, current + 1):
            raise HTTPException(404, "Contest not found")
        c = svc.get_or_create_contest(db, number)
    if clock.now() >= clock.aware(c.ends_at):
        raise HTTPException(409, "Contest is over")
    if not db.get(ContestEntry, (c.id, user.id)):
        db.add(ContestEntry(contest_id=c.id, user_id=user.id, registered_at=clock.now()))
        db.commit()
    return _contest_out(db, c, user)
