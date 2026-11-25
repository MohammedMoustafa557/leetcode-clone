from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Difficulty = Literal["Easy", "Medium", "Hard"]
Verdict = Literal[
    "Accepted", "Wrong Answer", "Runtime Error", "Compile Error", "Time Limit Exceeded"
]
ProblemStatus = Literal["solved", "attempted", "todo"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- auth ----------
class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    login: str = Field(description="username or email")
    password: str


class UserOut(ORM):
    id: int
    username: str
    email: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- catalog ----------
class TagOut(ORM):
    name: str
    slug: str
    count: int = 0


class CompanyOut(ORM):
    name: str
    slug: str
    count: int = 0


class ProblemCompanyOut(BaseModel):
    name: str
    slug: str
    frequency: float
    recency: str


class ProblemListItem(BaseModel):
    id: int
    frontend_id: int
    slug: str
    title: str
    difficulty: Difficulty
    tags: list[str]
    company_count: int
    frequency: float | None = None
    status: ProblemStatus = "todo"


class ProblemPage(BaseModel):
    items: list[ProblemListItem]
    total: int
    page: int
    page_size: int


class ProblemDetail(BaseModel):
    id: int
    frontend_id: int
    slug: str
    title: str
    difficulty: Difficulty
    description: str
    starter_code: str
    entry_point: str
    preamble: str
    test_code: str
    test_count: int
    released: date | None
    heavy_tests: bool = False
    tags: list[TagOut]
    companies: list[ProblemCompanyOut]
    status: ProblemStatus = "todo"


class SolutionOut(BaseModel):
    slug: str
    solution: str


# ---------- submissions ----------
class SubmissionIn(BaseModel):
    problem_slug: str
    code: str = Field(max_length=100_000)
    language: Literal["python3"] = "python3"
    verdict: Verdict
    passed: int = Field(ge=0)
    total: int = Field(ge=0)
    runtime_ms: float | None = Field(default=None, ge=0)


class SubmissionOut(BaseModel):
    id: int
    problem_slug: str
    problem_title: str
    verdict: Verdict
    passed: int
    total: int
    runtime_ms: float | None
    language: str
    created_at: datetime
    code: str | None = None


class DifficultyCount(BaseModel):
    solved: int
    total: int


class TagStat(BaseModel):
    name: str
    slug: str
    attempted: int
    solved: int
    submissions: int
    accuracy: float


class StatsOut(BaseModel):
    solved: int
    attempted: int
    total_problems: int
    submissions: int
    acceptance_rate: float
    by_difficulty: dict[str, DifficultyCount]
    streak: int
    max_streak: int
    calendar: dict[str, int]
    top_tags: list[TagOut]
    tag_stats: list[TagStat] = []
    strengths: list[TagStat] = []
    weaknesses: list[TagStat] = []
