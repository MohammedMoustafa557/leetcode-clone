from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import DB, CurrentUser
from app.models import Problem, Submission, Tag, problem_tags
from app.schemas.schemas import (
    DifficultyCount,
    StatsOut,
    SubmissionIn,
    SubmissionOut,
    TagOut,
    TagStat,
)
from app.services import notion
from app.services.progress import status_map, streaks

router = APIRouter(tags=["submissions"])


def _out(s: Submission, include_code: bool = False) -> SubmissionOut:
    return SubmissionOut(
        id=s.id, problem_slug=s.problem.slug, problem_title=s.problem.title, verdict=s.verdict,
        passed=s.passed, total=s.total, runtime_ms=s.runtime_ms, language=s.language,
        created_at=s.created_at, code=s.code if include_code else None,
    )


@router.post("/submissions", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
def create_submission(body: SubmissionIn, db: DB, user: CurrentUser, background: BackgroundTasks) -> SubmissionOut:
    problem = db.scalar(select(Problem).where(Problem.slug == body.problem_slug))
    if problem is None:
        raise HTTPException(404, "Problem not found")
    if body.passed > body.total or body.total > problem.test_count:
        raise HTTPException(422, "passed/total do not match this problem's test suite")
    if body.verdict == "Accepted" and body.passed != problem.test_count:
        raise HTTPException(422, "Accepted requires passing every test case")
    sub = Submission(
        user_id=user.id, problem_id=problem.id, code=body.code, language=body.language,
        verdict=body.verdict, passed=body.passed, total=body.total, runtime_ms=body.runtime_ms,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    if sub.verdict == "Accepted" and notion.enabled_for(user):
        background.add_task(notion.sync_first_solve, user.id, problem.id)
    return _out(sub, include_code=True)


@router.get("/submissions", response_model=list[SubmissionOut])
def list_submissions(
    db: DB,
    user: CurrentUser,
    problem_slug: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[SubmissionOut]:
    stmt = select(Submission).where(Submission.user_id == user.id)
    if problem_slug:
        stmt = stmt.join(Problem).where(Problem.slug == problem_slug)
    stmt = stmt.order_by(Submission.created_at.desc(), Submission.id.desc()).limit(limit)
    return [_out(s) for s in db.scalars(stmt)]


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
def get_submission(submission_id: int, db: DB, user: CurrentUser) -> SubmissionOut:
    s = db.get(Submission, submission_id)
    if s is None or s.user_id != user.id:
        raise HTTPException(404, "Submission not found")
    return _out(s, include_code=True)


@router.get("/me/stats", response_model=StatsOut)
def my_stats(db: DB, user: CurrentUser) -> StatsOut:
    statuses = status_map(db, user.id)
    solved_ids = [pid for pid, s in statuses.items() if s == "solved"]

    totals = dict(db.execute(select(Problem.difficulty, func.count()).group_by(Problem.difficulty)).all())
    solved_by = dict(
        db.execute(
            select(Problem.difficulty, func.count())
            .where(Problem.id.in_(solved_ids))
            .group_by(Problem.difficulty)
        ).all()
    ) if solved_ids else {}
    by_difficulty = {
        d: DifficultyCount(solved=solved_by.get(d, 0), total=totals.get(d, 0))
        for d in ("Easy", "Medium", "Hard")
    }

    subs = db.execute(
        select(Submission.verdict, Submission.created_at).where(Submission.user_id == user.id)
    ).all()
    accepted = sum(1 for v, _ in subs if v == "Accepted")
    since = datetime.now(UTC).date() - timedelta(days=365)
    calendar = Counter(
        c.date().isoformat() for _, c in subs if c.date() >= since
    )
    active = {c.date() for v, c in subs if v == "Accepted"}
    current, longest = streaks(active, datetime.now(UTC).date())

    top_tags = []
    if solved_ids:
        rows = db.execute(
            select(Tag.name, Tag.slug, func.count())
            .join(problem_tags, problem_tags.c.tag_id == Tag.id)
            .where(problem_tags.c.problem_id.in_(solved_ids))
            .group_by(Tag.id)
            .order_by(func.count().desc())
            .limit(8)
        )
        top_tags = [TagOut(name=n, slug=s, count=c) for n, s, c in rows]

    tag_rows = db.execute(
        select(Tag.name, Tag.slug, Submission.problem_id, Submission.verdict)
        .join(problem_tags, problem_tags.c.problem_id == Submission.problem_id)
        .join(Tag, Tag.id == problem_tags.c.tag_id)
        .where(Submission.user_id == user.id)
    ).all()
    per: dict[str, dict] = {}
    for name, slug, pid, verdict in tag_rows:
        t = per.setdefault(slug, {"name": name, "slug": slug, "subs": 0, "acc": 0, "problems": set(), "solved": set()})
        t["subs"] += 1
        t["problems"].add(pid)
        if verdict == "Accepted":
            t["acc"] += 1
            t["solved"].add(pid)
    tag_stats = [
        TagStat(name=t["name"], slug=t["slug"], attempted=len(t["problems"]), solved=len(t["solved"]),
                submissions=t["subs"], accuracy=round(100 * t["acc"] / t["subs"], 1))
        for t in per.values()
    ]
    tag_stats.sort(key=lambda t: (-t.solved, -t.accuracy))
    ranked = [t for t in tag_stats if t.submissions >= 2]
    strengths = sorted(ranked, key=lambda t: (-t.accuracy, -t.solved))[:5]
    weaknesses = sorted(ranked, key=lambda t: (t.accuracy, -t.submissions))[:5]

    return StatsOut(
        tag_stats=tag_stats,
        strengths=strengths,
        weaknesses=[w for w in weaknesses if w.accuracy < 100],
        solved=len(solved_ids),
        attempted=sum(1 for s in statuses.values() if s == "attempted"),
        total_problems=sum(totals.values()),
        submissions=len(subs),
        acceptance_rate=round(100 * accepted / len(subs), 1) if subs else 0.0,
        by_difficulty=by_difficulty,
        streak=current,
        max_streak=longest,
        calendar=dict(calendar),
        top_tags=top_tags,
    )
