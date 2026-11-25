"""45-minute mock interviews: 2 real problems a company asks, a countdown and a score."""

import random
from datetime import timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DB, CurrentUser
from app.models import Company, InterviewSession, Problem, ProblemCompany, Submission
from app.services import clock

router = APIRouter(prefix="/interviews", tags=["interviews"])
DURATION = timedelta(minutes=45)


class InterviewIn(BaseModel):
    company_slug: str


def _out(db, s: InterviewSession) -> dict:
    ids = [int(x) for x in s.problem_ids.split(",")]
    problems = {p.id: p for p in db.scalars(select(Problem).where(Problem.id.in_(ids)))}
    start, end = clock.aware(s.started_at), clock.aware(s.finished_at or s.ends_at)
    end = min(end, clock.aware(s.ends_at))
    solved_ids = set(db.scalars(select(Submission.problem_id).where(
        Submission.user_id == s.user_id, Submission.problem_id.in_(ids), Submission.verdict == "Accepted",
        Submission.created_at >= start, Submission.created_at <= end)))
    now = clock.now()
    return {
        "id": s.id, "company": {"name": s.company.name, "slug": s.company.slug},
        "started_at": start.isoformat(), "ends_at": clock.aware(s.ends_at).isoformat(),
        "finished_at": clock.aware(s.finished_at).isoformat() if s.finished_at else None,
        "seconds_left": max(0, int((clock.aware(s.ends_at) - now).total_seconds())) if not s.finished_at else 0,
        "score": s.score,
        "problems": [{"slug": problems[i].slug, "title": problems[i].title, "difficulty": problems[i].difficulty,
                      "solved": i in solved_ids} for i in ids if i in problems],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def start(body: InterviewIn, db: DB, user: CurrentUser) -> dict:
    company = db.scalar(select(Company).where(Company.slug == body.company_slug))
    if company is None:
        raise HTTPException(404, "Company not found")
    rows = db.execute(select(Problem.id, Problem.difficulty).join(ProblemCompany)
                      .where(ProblemCompany.company_id == company.id, Problem.heavy_tests.is_(False))).all()
    if len(rows) < 2:
        raise HTTPException(422, "This company has fewer than 2 problems in the catalog")
    easy_med = [r.id for r in rows if r.difficulty != "Hard"]
    first = random.choice(easy_med or [r.id for r in rows])
    second = random.choice([r.id for r in rows if r.id != first])
    now = clock.now()
    s = InterviewSession(user_id=user.id, company_id=company.id, problem_ids=f"{first},{second}",
                         started_at=now, ends_at=now + DURATION)
    db.add(s)
    db.commit()
    db.refresh(s)
    return _out(db, s)


@router.get("")
def history(db: DB, user: CurrentUser) -> list[dict]:
    rows = db.scalars(select(InterviewSession).where(InterviewSession.user_id == user.id)
                      .order_by(InterviewSession.id.desc()).limit(50))
    return [_out(db, s) for s in rows]


def _get(db, user, session_id: int) -> InterviewSession:
    s = db.get(InterviewSession, session_id)
    if s is None or s.user_id != user.id:
        raise HTTPException(404, "Interview not found")
    return s


@router.get("/{session_id}")
def get_one(session_id: int, db: DB, user: CurrentUser) -> dict:
    return _out(db, _get(db, user, session_id))


@router.post("/{session_id}/finish")
def finish(session_id: int, db: DB, user: CurrentUser) -> dict:
    s = _get(db, user, session_id)
    if s.finished_at is None:
        s.finished_at = min(clock.now(), clock.aware(s.ends_at))
        db.flush()
        result = _out(db, s)
        solved = sum(p["solved"] for p in result["problems"])
        used = (clock.aware(s.finished_at) - clock.aware(s.started_at)).total_seconds()
        # 40 points per solved problem + up to 20 for finishing early with everything solved
        bonus = round(20 * max(0.0, 1 - used / DURATION.total_seconds())) if solved == 2 else 0
        s.score = 40 * solved + bonus
        db.commit()
    return _out(db, s)
