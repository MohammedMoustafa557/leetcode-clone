from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import false

from app.db import Base
from app.services import clock


def utcnow() -> datetime:
    return clock.now()


problem_tags = Table(
    "problem_tags",
    Base.metadata,
    Column("problem_id", ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    rating: Mapped[int] = mapped_column(Integer, default=1500, server_default="1500")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    submissions: Mapped[list["Submission"]] = relationship(back_populates="user")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(primary_key=True)
    frontend_id: Mapped[int] = mapped_column(Integer, index=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    difficulty: Mapped[str] = mapped_column(String(8), index=True)
    description: Mapped[str] = mapped_column(Text)
    starter_code: Mapped[str] = mapped_column(Text)
    entry_point: Mapped[str] = mapped_column(String(255))
    preamble: Mapped[str] = mapped_column(Text)
    test_code: Mapped[str] = mapped_column(Text)
    test_count: Mapped[int] = mapped_column(Integer, default=0)
    solution: Mapped[str] = mapped_column(Text, default="")
    released: Mapped[date | None] = mapped_column(Date, nullable=True)
    # test suite is unusually heavy (reference solution exceeds normal limits)
    heavy_tests: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    tags: Mapped[list[Tag]] = relationship(secondary=problem_tags, lazy="selectin")
    companies: Mapped[list["ProblemCompany"]] = relationship(
        back_populates="problem", lazy="selectin", cascade="all, delete-orphan"
    )


class ProblemCompany(Base):
    __tablename__ = "problem_companies"

    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True
    )
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    frequency: Mapped[float] = mapped_column(Float, default=0)
    # most recent window the problem was reported in: 30d, 3m, 6m, 6m+
    recency: Mapped[str] = mapped_column(String(8), default="6m+")

    problem: Mapped[Problem] = relationship(back_populates="companies")
    company: Mapped[Company] = relationship(lazy="joined")


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problems.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(16), default="python3")
    verdict: Mapped[str] = mapped_column(String(32))
    passed: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    runtime_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )

    user: Mapped[User] = relationship(back_populates="submissions")
    problem: Mapped[Problem] = relationship()


class ProblemGuide(Base):
    """Cached per-problem study guide (hints, explanation, interview sentences)."""

    __tablename__ = "problem_guides"

    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True)
    source: Mapped[str] = mapped_column(String(16))  # "auto" (deterministic) or "llm"
    data: Mapped[str] = mapped_column(Text)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    problem_ids: Mapped[str] = mapped_column(String(64))  # comma separated
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    company: Mapped[Company] = relationship(lazy="joined")


class Contest(Base):
    __tablename__ = "contests"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(64))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    problem_ids: Mapped[str] = mapped_column(String(64))  # comma separated, in order
    rated: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())


class ContestEntry(Base):
    __tablename__ = "contest_entries"

    contest_id: Mapped[int] = mapped_column(ForeignKey("contests.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    score: Mapped[int] = mapped_column(Integer, default=0)
    penalty_seconds: Mapped[int] = mapped_column(Integer, default=0)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_after: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped[User] = relationship(lazy="joined")


class NotionSync(Base):
    """Problems already pushed to the owner's Notion tracker (so we only sync first solves once)."""

    __tablename__ = "notion_syncs"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[str] = mapped_column(String(16))  # ok | error
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
