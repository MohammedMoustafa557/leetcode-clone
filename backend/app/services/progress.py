from datetime import date, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Submission


def status_map(db: Session, user_id: int, problem_ids: list[int] | None = None) -> dict[int, str]:
    """problem_id -> 'solved' | 'attempted' for one user."""
    solved = func.max(case((Submission.verdict == "Accepted", 1), else_=0))
    stmt = (
        select(Submission.problem_id, solved)
        .where(Submission.user_id == user_id)
        .group_by(Submission.problem_id)
    )
    if problem_ids is not None:
        stmt = stmt.where(Submission.problem_id.in_(problem_ids))
    return {pid: ("solved" if s else "attempted") for pid, s in db.execute(stmt)}


def streaks(active_days: set[date], today: date) -> tuple[int, int]:
    """(current streak, longest streak) of consecutive days with an Accepted submission.

    The current streak survives until the end of the next day, so solving
    yesterday but not yet today still counts.
    """
    if not active_days:
        return 0, 0
    longest = run = 0
    prev: date | None = None
    for d in sorted(active_days):
        run = run + 1 if prev is not None and d - prev == timedelta(days=1) else 1
        longest = max(longest, run)
        prev = d
    current = 0
    cursor = today if today in active_days else today - timedelta(days=1)
    while cursor in active_days:
        current += 1
        cursor -= timedelta(days=1)
    return current, longest
