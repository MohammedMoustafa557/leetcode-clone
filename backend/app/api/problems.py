import random
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import case, func, or_, select

from app.api.deps import DB, OptionalUser
from app.models import Company, Problem, ProblemCompany, Tag, problem_tags
from app.schemas.schemas import (
    CompanyOut,
    ProblemCompanyOut,
    ProblemDetail,
    ProblemListItem,
    ProblemPage,
    SolutionOut,
    TagOut,
)
from app.services.progress import status_map

router = APIRouter(tags=["problems"])

SortKey = Literal["id", "title", "difficulty", "frequency"]


def _companies(p: Problem) -> list[ProblemCompanyOut]:
    return sorted(
        (
            ProblemCompanyOut(
                name=pc.company.name, slug=pc.company.slug, frequency=pc.frequency, recency=pc.recency
            )
            for pc in p.companies
        ),
        key=lambda c: -c.frequency,
    )


@router.get("/problems", response_model=ProblemPage)
def list_problems(
    db: DB,
    user: OptionalUser,
    q: Annotated[str | None, Query(max_length=100)] = None,
    difficulty: Literal["Easy", "Medium", "Hard"] | None = None,
    tag: Annotated[list[str] | None, Query()] = None,
    company: str | None = None,
    status: Literal["solved", "attempted", "todo"] | None = None,
    sort: SortKey = "id",
    order: Literal["asc", "desc"] = "asc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ProblemPage:
    stmt = select(Problem)
    freq_col = None
    if q:
        like = f"%{q.strip().lower()}%"
        conds = [func.lower(Problem.title).like(like), Problem.slug.like(like)]
        if q.strip().isdigit():
            conds.append(Problem.frontend_id == int(q.strip()))
        stmt = stmt.where(or_(*conds))
    if difficulty:
        stmt = stmt.where(Problem.difficulty == difficulty)
    for t in tag or []:  # AND semantics, like LeetCode
        sub = (
            select(problem_tags.c.problem_id)
            .join(Tag, Tag.id == problem_tags.c.tag_id)
            .where(Tag.slug == t)
        )
        stmt = stmt.where(Problem.id.in_(sub))
    if company:
        stmt = stmt.join(ProblemCompany, ProblemCompany.problem_id == Problem.id).join(
            Company, Company.id == ProblemCompany.company_id
        ).where(Company.slug == company)
        freq_col = ProblemCompany.frequency
        stmt = stmt.add_columns(freq_col)

    statuses: dict[int, str] = status_map(db, user.id) if user else {}
    if status and user:
        ids = [pid for pid, s in statuses.items() if s == status]
        if status == "todo":
            stmt = stmt.where(Problem.id.not_in(list(statuses)))
        else:
            stmt = stmt.where(Problem.id.in_(ids))
    elif status in ("solved", "attempted"):
        stmt = stmt.where(False)

    total = db.scalar(select(func.count()).select_from(stmt.with_only_columns(Problem.id).subquery()))

    diff_rank = case(
        (Problem.difficulty == "Easy", 1), (Problem.difficulty == "Medium", 2), else_=3
    )
    sort_cols = {
        "id": Problem.frontend_id,
        "title": Problem.title,
        "difficulty": diff_rank,
        "frequency": freq_col if freq_col is not None else Problem.frontend_id,
    }
    col = sort_cols[sort]
    stmt = stmt.order_by(col.desc() if order == "desc" else col.asc(), Problem.frontend_id)
    rows = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).all()

    items = []
    for row in rows:
        p: Problem = row[0]
        items.append(
            ProblemListItem(
                id=p.id,
                frontend_id=p.frontend_id,
                slug=p.slug,
                title=p.title,
                difficulty=p.difficulty,
                tags=[t.name for t in p.tags],
                company_count=len(p.companies),
                frequency=row[1] if freq_col is not None else None,
                status=statuses.get(p.id, "todo"),
            )
        )
    return ProblemPage(items=items, total=total or 0, page=page, page_size=page_size)


@router.get("/problems/random", response_model=ProblemListItem)
def random_problem(
    db: DB, user: OptionalUser, difficulty: Literal["Easy", "Medium", "Hard"] | None = None
) -> ProblemListItem:
    stmt = select(Problem.id)
    if difficulty:
        stmt = stmt.where(Problem.difficulty == difficulty)
    ids = list(db.scalars(stmt))
    if user:
        solved = {pid for pid, s in status_map(db, user.id).items() if s == "solved"}
        ids = [i for i in ids if i not in solved] or ids
    if not ids:
        raise HTTPException(404, "No problems loaded. Run the seed script first.")
    p = db.get(Problem, random.choice(ids))
    return ProblemListItem(
        id=p.id, frontend_id=p.frontend_id, slug=p.slug, title=p.title, difficulty=p.difficulty,
        tags=[t.name for t in p.tags], company_count=len(p.companies),
    )


@router.get("/problems/{slug}", response_model=ProblemDetail)
def get_problem(slug: str, db: DB, user: OptionalUser) -> ProblemDetail:
    p = db.scalar(select(Problem).where(Problem.slug == slug))
    if p is None:
        raise HTTPException(404, "Problem not found")
    status = status_map(db, user.id, [p.id]).get(p.id, "todo") if user else "todo"
    return ProblemDetail(
        id=p.id, frontend_id=p.frontend_id, slug=p.slug, title=p.title, difficulty=p.difficulty,
        description=p.description, starter_code=p.starter_code, entry_point=p.entry_point,
        preamble=p.preamble, test_code=p.test_code, test_count=p.test_count, released=p.released,
        heavy_tests=bool(p.heavy_tests),
        tags=[TagOut(name=t.name, slug=t.slug) for t in p.tags],
        companies=_companies(p), status=status,
    )


@router.get("/problems/{slug}/solution", response_model=SolutionOut)
def get_solution(slug: str, db: DB) -> SolutionOut:
    p = db.scalar(select(Problem).where(Problem.slug == slug))
    if p is None:
        raise HTTPException(404, "Problem not found")
    return SolutionOut(slug=p.slug, solution=p.solution)


@router.get("/tags", response_model=list[TagOut])
def list_tags(db: DB) -> list[TagOut]:
    rows = db.execute(
        select(Tag.name, Tag.slug, func.count(problem_tags.c.problem_id))
        .join(problem_tags, problem_tags.c.tag_id == Tag.id)
        .group_by(Tag.id)
        .order_by(func.count(problem_tags.c.problem_id).desc())
    )
    return [TagOut(name=n, slug=s, count=c) for n, s, c in rows]


@router.get("/companies", response_model=list[CompanyOut])
def list_companies(db: DB) -> list[CompanyOut]:
    rows = db.execute(
        select(Company.name, Company.slug, func.count(ProblemCompany.problem_id))
        .join(ProblemCompany, ProblemCompany.company_id == Company.id)
        .group_by(Company.id)
        .order_by(func.count(ProblemCompany.problem_id).desc())
    )
    return [CompanyOut(name=n, slug=s, count=c) for n, s, c in rows]

