"""In-app reading of the downloaded books (System Design Primer, Karan's course, Behavioral handbook)."""

import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services import docs

router = APIRouter(prefix="/docs", tags=["learn"])


def _credit(meta: dict) -> dict:
    return {k: meta.get(k) for k in ("title", "author", "repo", "license", "license_url", "notice")}


def _get(key: str) -> dict:
    meta = docs.load_collection(key)
    if meta is None:
        raise HTTPException(404, "Book not downloaded. Run: python -m scripts.fetch_docs")
    return meta


@router.get("")
def list_books() -> list[dict]:
    out = []
    for key in docs.available():
        meta = docs.load_collection(key)
        out.append({"id": key, **_credit(meta), "chapters": len(meta["chapters"])})
    return out


@router.get("/{key}")
def book(key: str) -> dict:
    meta = _get(key)
    return {"id": key, **_credit(meta), "chapters": [{"id": c["id"], "title": c["title"]} for c in meta["chapters"]]}


@router.get("/{key}/assets/{name}")
def asset(key: str, name: str) -> FileResponse:
    if not re.fullmatch(r"[0-9a-f]{16}\.(png|jpe?g|gif|svg|webp)", name) or key not in docs.available():
        raise HTTPException(404, "Not found")
    path = docs.DOCS_DIR / key / "assets" / name
    if not path.exists():
        raise HTTPException(404, "Not found")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=604800"})


@router.get("/{key}/{chapter_id}")
def chapter(key: str, chapter_id: str) -> dict:
    meta = _get(key)
    chapters = meta["chapters"]
    idx = next((i for i, c in enumerate(chapters) if c["id"] == chapter_id), None)
    if idx is None:
        raise HTTPException(404, "Chapter not found")
    c = chapters[idx]
    nav = lambda j: {"id": chapters[j]["id"], "title": chapters[j]["title"]} if 0 <= j < len(chapters) else None  # noqa: E731
    return {
        "id": c["id"], "title": c["title"], "markdown": docs.render(key, meta, c["body"]),
        "prev": nav(idx - 1), "next": nav(idx + 1), "credit": _credit(meta),
    }
