"""Points, badges, leaderboard and contest rating (all computed server-side)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Contest, ContestEntry, InterviewSession, Problem, Submission, User
from app.services import clock
from app.services.progress import streaks

POINTS = {"Easy": 10, "Medium": 20, "Hard": 40}
CONTEST_POINTS = [3, 4, 5, 6]  # Q1..Q4, like LeetCode weekly contests
WRONG_PENALTY_S = 5 * 60
ELO_K = 64


@dataclass
class UserSummary:
    user: User
    solved: dict[str, int]
    points: int
    streak: int
    max_streak: int
    contests: int


def solved_by_difficulty(db: Session, user_id: int) -> dict[str, int]:
    sub = (
        select(Submission.problem_id).where(Submission.user_id == user_id, Submission.verdict == "Accepted")
        .distinct().subquery()
    )
    rows = db.execute(select(Problem.difficulty, func.count()).join(sub, sub.c.problem_id == Problem.id)
                      .group_by(Problem.difficulty)).all()
    d = {"Easy": 0, "Medium": 0, "Hard": 0}
    d.update(dict(rows))
    return d


def summarize(db: Session, user: User) -> UserSummary:
    solved = solved_by_difficulty(db, user.id)
    days = {c.date() for (c,) in db.execute(
        select(Submission.created_at).where(Submission.user_id == user.id, Submission.verdict == "Accepted"))}
    cur, longest = streaks(days, clock.now().date())
    contests = db.scalar(select(func.count()).select_from(ContestEntry).where(
        ContestEntry.user_id == user.id, ContestEntry.rating_after.is_not(None))) or 0
    points = sum(POINTS[k] * v for k, v in solved.items())
    return UserSummary(user, solved, points, cur, longest, contests)


def global_rank(db: Session, user: User) -> int | None:
    """Rank by rating among users who finished at least one rated contest."""
    rated = select(ContestEntry.user_id).where(ContestEntry.rating_after.is_not(None)).distinct()
    if not db.scalar(select(func.count()).select_from(rated.where(ContestEntry.user_id == user.id).subquery())):
        return None
    higher = db.scalar(select(func.count()).select_from(User).where(User.id.in_(rated), User.rating > user.rating))
    return (higher or 0) + 1


BADGES = [
    ("first-solve", "First Blood", "Solve your first problem"),
    ("solved-10", "Getting Started", "Solve 10 problems"),
    ("solved-50", "Problem Solver", "Solve 50 problems"),
    ("solved-100", "Centurion", "Solve 100 problems"),
    ("hard-5", "Hard Hitter", "Solve 5 Hard problems"),
    ("streak-7", "7-Day Streak", "Solve something 7 days in a row"),
    ("streak-30", "30-Day Streak", "Solve something 30 days in a row"),
    ("contest-1", "Contestant", "Finish a weekly contest"),
    ("interview-1", "Mock Interviewee", "Finish a 45-minute mock interview"),
    ("knight", "Knight", "Reach a contest rating of 1850"),
]


def badges(db: Session, s: UserSummary) -> list[dict]:
    total = sum(s.solved.values())
    interviews = db.scalar(select(func.count()).select_from(InterviewSession).where(
        InterviewSession.user_id == s.user.id, InterviewSession.finished_at.is_not(None))) or 0
    earned = {
        "first-solve": total >= 1, "solved-10": total >= 10, "solved-50": total >= 50, "solved-100": total >= 100,
        "hard-5": s.solved["Hard"] >= 5, "streak-7": s.max_streak >= 7, "streak-30": s.max_streak >= 30,
        "contest-1": s.contests >= 1, "interview-1": interviews >= 1, "knight": s.user.rating >= 1850,
    }
    return [{"id": i, "name": n, "description": d, "earned": earned[i]} for i, n, d in BADGES]


# ------------------------------------------------------------------ contests
def contest_window(number: int) -> tuple[datetime, datetime]:
    s = get_settings()
    first = datetime.combine(date.fromisoformat(s.contest_first_date), datetime.min.time(), UTC)
    hh, mm = (int(x) for x in s.contest_start_utc.split(":"))
    start = first + timedelta(weeks=number - 1, hours=hh, minutes=mm)
    return start, start + timedelta(minutes=s.contest_minutes)


def contest_number_at(now: datetime) -> int:
    """The contest that is running now, or the next one if none is running."""
    s = get_settings()
    first = datetime.combine(date.fromisoformat(s.contest_first_date), datetime.min.time(), UTC)
    n = max(1, (now - first).days // 7 + 1)
    _, end = contest_window(n)
    return n + 1 if now >= end else n


def _pick_problems(db: Session, number: int) -> list[int]:
    plan = [("Easy",), ("Medium",), ("Medium",), ("Hard",)]
    chosen: list[int] = []
    for i, (diff,) in enumerate(plan):
        ids = list(db.scalars(select(Problem.id).where(
            Problem.difficulty == diff, Problem.heavy_tests.is_(False), Problem.id.not_in(chosen or [0])
        ).order_by(Problem.id)))
        if not ids:  # small catalogs (tests/CI): fall back to any problem
            ids = list(db.scalars(select(Problem.id).where(Problem.id.not_in(chosen or [0])).order_by(Problem.id)))
        if not ids:
            break
        h = int(hashlib.sha256(f"contest-{number}-{i}".encode()).hexdigest(), 16)
        chosen.append(ids[h % len(ids)])
    return chosen


def get_or_create_contest(db: Session, number: int) -> Contest:
    c = db.scalar(select(Contest).where(Contest.number == number))
    if c:
        return c
    start, end = contest_window(number)
    c = Contest(number=number, title=f"Weekly Contest {number}", starts_at=start, ends_at=end,
                problem_ids=",".join(map(str, _pick_problems(db, number))))
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def contest_problem_ids(c: Contest) -> list[int]:
    return [int(x) for x in c.problem_ids.split(",") if x]


def score_entry(db: Session, c: Contest, user_id: int) -> tuple[int, int, list[dict]]:
    """(score, penalty seconds, per-problem result) from submissions inside the window."""
    start, end = clock.aware(c.starts_at), clock.aware(c.ends_at)
    subs = db.execute(select(Submission.problem_id, Submission.verdict, Submission.created_at).where(
        Submission.user_id == user_id, Submission.problem_id.in_(contest_problem_ids(c)),
    ).order_by(Submission.created_at, Submission.id)).all()
    score = penalty = 0
    results = []
    for idx, pid in enumerate(contest_problem_ids(c)):
        wrong, solved_at = 0, None
        for spid, verdict, created in subs:
            created = clock.aware(created)
            if spid != pid or not (start <= created < end) or solved_at:
                continue
            if verdict == "Accepted":
                solved_at = created
            elif verdict != "Compile Error":
                wrong += 1
        if solved_at:
            score += CONTEST_POINTS[idx]
            penalty = max(penalty, int((solved_at - start).total_seconds()))
            penalty += wrong * WRONG_PENALTY_S
        results.append({"problem_id": pid, "solved": solved_at is not None, "wrong": wrong,
                        "solved_at": solved_at.isoformat() if solved_at else None})
    return score, penalty, results


def standings(db: Session, c: Contest) -> list[ContestEntry]:
    entries = list(db.scalars(select(ContestEntry).where(ContestEntry.contest_id == c.id)))
    if not c.rated:
        for e in entries:
            e.score, e.penalty_seconds, _ = score_entry(db, c, e.user_id)
    entries.sort(key=lambda e: (-e.score, e.penalty_seconds, e.registered_at))
    return entries


def elo_deltas(ratings: list[int], ranks: list[int], k: int = ELO_K) -> list[int]:
    """Multi-player Elo: everyone plays everyone; beating a player scores 1, a tie 0.5."""
    n = len(ratings)
    if n < 2:
        return [0] * n
    out = []
    for i in range(n):
        expected = actual = 0.0
        for j in range(n):
            if i == j:
                continue
            expected += 1 / (1 + 10 ** ((ratings[j] - ratings[i]) / 400))
            actual += 1.0 if ranks[i] < ranks[j] else 0.5 if ranks[i] == ranks[j] else 0.0
        out.append(round(k * (actual - expected) / (n - 1)))
    return out


def finalize_if_over(db: Session, c: Contest) -> None:
    if c.rated or clock.now() < clock.aware(c.ends_at):
        return
    entries = standings(db, c)
    ranks: list[int] = []
    for i, e in enumerate(entries):
        prev = entries[i - 1] if i else None
        same = prev and (prev.score, prev.penalty_seconds) == (e.score, e.penalty_seconds)
        ranks.append(ranks[-1] if same else i + 1)
    deltas = elo_deltas([e.user.rating for e in entries], ranks)
    for e, rank, delta in zip(entries, ranks, deltas, strict=True):
        e.rank = rank
        e.rating_before = e.user.rating
        e.rating_after = e.user.rating + delta
        e.user.rating = e.rating_after
    c.rated = True
    db.commit()
