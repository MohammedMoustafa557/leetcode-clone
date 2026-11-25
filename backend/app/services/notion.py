"""Optional: push a user's first-time solves to a Notion database (off unless NOTION_TOKEN is set).

The target database schema is read first, so only properties that exist are filled
(Problem/Name title, Difficulty, Topic, Status, Date, Link, Notes).
"""

from __future__ import annotations

import logging

import httpx
from sqlalchemy import select

from app.core.config import get_settings
from app.db import SessionLocal
from app.models import NotionSync, Problem, Submission, User
from app.services import clock

log = logging.getLogger(__name__)
API = "https://api.notion.com/v1"
HEADERS_VERSION = "2022-06-28"


def enabled_for(user: User) -> bool:
    s = get_settings()
    return bool(s.notion_token and s.notion_database_id and s.notion_sync_username
                and user.username == s.notion_sync_username)


def _value(kind: str, value: str):
    if kind == "title":
        return {"title": [{"text": {"content": value}}]}
    if kind == "rich_text":
        return {"rich_text": [{"text": {"content": value}}]}
    if kind in ("select", "status"):
        return {kind: {"name": value}}
    if kind == "multi_select":
        return {"multi_select": [{"name": v.strip()} for v in value.split(",") if v.strip()][:5]}
    if kind == "date":
        return {"date": {"start": value}}
    if kind == "url":
        return {"url": value}
    return None


def build_properties(schema: dict, p: Problem, day: str, site_url: str) -> dict:
    wanted = {
        "difficulty": p.difficulty,
        "topic": ", ".join(t.name for t in p.tags[:3]) or "General",
        "status": "Solved",
        "date": day,
        "link": f"{site_url.rstrip('/')}/problems/{p.slug}",
        "notes": "Solved on CodeArena",
    }
    props: dict = {}
    for name, meta in schema.items():
        kind = meta.get("type")
        if kind == "title":
            props[name] = _value("title", p.title)
        elif name.lower() in wanted and (v := _value(kind, wanted[name.lower()])):
            props[name] = v
    return props


def sync_first_solve(user_id: int, problem_id: int, client: httpx.Client | None = None) -> str:
    """Runs as a background task. Returns 'ok', 'skipped' or 'error'."""
    s = get_settings()
    with SessionLocal() as db:
        user = db.get(User, user_id)
        p = db.get(Problem, problem_id)
        if not user or not p or not enabled_for(user) or db.get(NotionSync, (user_id, problem_id)):
            return "skipped"
        accepted = db.scalar(select(Submission.id).where(
            Submission.user_id == user_id, Submission.problem_id == problem_id, Submission.verdict == "Accepted"
        ).limit(2).offset(1))
        if accepted:  # not the first solve
            return "skipped"
        http = client or httpx.Client(timeout=20)
        headers = {"Authorization": f"Bearer {s.notion_token}", "Notion-Version": HEADERS_VERSION}
        try:
            schema = http.get(f"{API}/databases/{s.notion_database_id}", headers=headers)
            schema.raise_for_status()
            props = build_properties(schema.json().get("properties", {}), p, clock.now().date().isoformat(),
                                     s.public_site_url)
            r = http.post(f"{API}/pages", headers=headers,
                          json={"parent": {"database_id": s.notion_database_id}, "properties": props})
            r.raise_for_status()
            status, detail = "ok", r.json().get("id", "")
        except httpx.HTTPError as exc:
            log.warning("Notion sync failed: %s", exc)
            status, detail = "error", str(exc)[:500]
        db.add(NotionSync(user_id=user_id, problem_id=problem_id, status=status, detail=detail))
        db.commit()
        return status
