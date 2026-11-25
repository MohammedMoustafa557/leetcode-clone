"""Serve the downloaded books (scripts/fetch_docs.py) as in-app chapters.

The stored markdown is never edited. At render time we only:
  * cut the book into chapters at its own headings,
  * point image URLs at our /api/docs/assets endpoint,
  * point in-book "#anchor" links at the chapter that holds the anchor,
  * drop MDX-only lines (``import ...`` / ``<InDocAd />``) from the MIT handbook.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "docs"
FENCE = re.compile(r"^(```|~~~)")


def gh_anchor(title: str) -> str:
    a = re.sub(r"<[^>]+>", "", title).strip().lower()
    a = re.sub(r"[^\w\- ]", "", a)
    return a.replace(" ", "-")


def _headings(text: str, level: int):
    """Yield (line_index, title) for headings of exactly `level`, ignoring fenced code."""
    in_code = False
    prefix = "#" * level + " "
    for i, line in enumerate(text.split("\n")):
        if FENCE.match(line.strip()):
            in_code = not in_code
        elif not in_code and line.startswith(prefix):
            yield i, line[len(prefix):].strip()


def _front_matter(text: str) -> tuple[dict, str]:
    meta: dict = {}
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            for line in text[4:end].split("\n"):
                if ":" in line and not line.startswith(" "):
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip("'\"")
            text = text[end + 4:].lstrip("\n")
    return meta, text


@lru_cache
def load_collection(key: str) -> dict | None:
    root = DOCS_DIR / key
    mf = root / "manifest.json"
    if not mf.exists():
        return None
    meta = json.loads(mf.read_text(encoding="utf-8"))
    chapters: list[dict] = []
    for name in meta["files"]:
        text = (root / name).read_text(encoding="utf-8")
        if meta["split"] == 0:
            fm, body = _front_matter(text)
            body = "\n".join(
                ln for ln in body.split("\n")
                if not ln.startswith("import ") and not re.match(r"^\s*<[A-Z]\w*\s*/>\s*$", ln)
                and not re.match(r"^\s*</?head>\s*$|^\s*<meta ", ln)
            )
            chapters.append({"title": fm.get("title") or fm.get("sidebar_label") or name, "body": body})
            continue
        lines = text.split("\n")
        cuts = list(_headings(text, meta["split"]))
        if cuts and cuts[0][0] > 0:
            chapters.append({"title": "Introduction", "body": "\n".join(lines[: cuts[0][0]])})
        for n, (idx, title) in enumerate(cuts):
            end = cuts[n + 1][0] if n + 1 < len(cuts) else len(lines)
            chapters.append({"title": re.sub(r"<[^>]+>", "", title), "body": "\n".join(lines[idx:end])})
    for i, ch in enumerate(chapters):
        ch["id"] = f"{i:03d}-{gh_anchor(ch['title'])[:60] or 'section'}"
    anchors: dict[str, str] = {}
    for ch in chapters:
        for level in range(1, 7):
            for _, title in _headings(ch["body"], level):
                anchors.setdefault(gh_anchor(title), ch["id"])
    meta["chapters"] = chapters
    meta["anchors"] = anchors
    return meta


def available() -> list[str]:
    return sorted(p.name for p in DOCS_DIR.iterdir() if (p / "manifest.json").exists()) if DOCS_DIR.exists() else []


def render(key: str, meta: dict, body: str, api_prefix: str = "/api") -> str:
    images: dict[str, str] = meta.get("images", {})
    for src, local in sorted(images.items(), key=lambda kv: -len(kv[0])):
        body = body.replace(f"({src})", f"({api_prefix}/docs/{key}/assets/{local})")
        body = body.replace(f'src="{src}"', f'src="{api_prefix}/docs/{key}/assets/{local}"')

    def link(m: re.Match) -> str:
        anchor = m.group(1)
        chapter = meta["anchors"].get(anchor)
        return f"](/learn/docs/{key}/{chapter}#{anchor})" if chapter else m.group(0)

    body = re.sub(r"\]\(#([^)\s]+)\)", link, body)
    body = re.sub(r'href="#([^"]+)"', lambda m: (
        f'href="/learn/docs/{key}/{meta["anchors"][m.group(1)]}#{m.group(1)}"'
        if m.group(1) in meta["anchors"] else m.group(0)), body)
    return body
