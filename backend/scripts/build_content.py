"""Regenerate the committed learning content in app/content/ from upstream repos.

    python -m scripts.build_content

Everything written here is either MIT-licensed upstream content (kept with its
attribution), our own text, or titles + outbound links only (for sources whose
license does not allow redistribution or derivatives).
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "app" / "content"
RAW = "https://raw.githubusercontent.com/"


def fetch(path: str) -> str:
    req = urllib.request.Request(RAW + path, headers={"User-Agent": "codearena-content/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def gh_anchor(title: str) -> str:
    """GitHub's markdown heading anchor algorithm."""
    a = title.strip().lower()
    a = re.sub(r"[^\w\- ]", "", a)
    return a.replace(" ", "-")


def write(name: str, data) -> None:
    (OUT / name).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {name}")


# ---------------------------------------------------------------- NeetCode (MIT)
def neetcode() -> None:
    rows = json.loads(fetch("neetcode-gh/leetcode/main/.problemSiteData.json"))
    out = [
        {
            "title": r["problem"],
            "slug": r["link"].strip("/").split("/")[-1],
            "pattern": r.get("pattern", ""),
            "difficulty": r.get("difficulty", ""),
            "blind75": bool(r.get("blind75")),
            "neetcode150": bool(r.get("neetcode150")),
            "video": r.get("video") or None,
        }
        for r in rows
    ]
    write("neetcode.json", {
        "source": "https://github.com/neetcode-gh/leetcode", "license": "MIT", "problems": out,
    })


# ---------------------------------------------------------------- SQL Q&A (MIT)
def sql_qa() -> None:
    lines = fetch("xoraus/CrackingTheSQLInterview/master/README.md").split("\n")
    section, in_bank, cur, qs = None, False, None, []
    for ln in lines:
        if ln.startswith("## "):
            section = re.sub(r"^## (Section \d+:\s*)?", "", ln).strip()
            in_bank = False
            continue
        if ln.startswith("### "):
            in_bank = "Q&A Bank" in ln
            if cur:
                qs.append(cur)
                cur = None
            continue
        if not in_bank:
            continue
        m = re.match(r"^\*\*(\d+)\.\s+(.*?)\*\*\s*$", ln)
        if m:
            if cur:
                qs.append(cur)
            cur = {"number": int(m.group(1)), "section": section, "question": m.group(2).strip(), "answer": []}
        elif cur is not None and (ln.startswith(">") or not ln.strip()):
            cur["answer"].append(ln[2:] if ln.startswith("> ") else ln[1:])
    if cur:
        qs.append(cur)
    for q in qs:
        q["answer"] = "\n".join(q["answer"]).strip()
    write("sql_qa.json", {
        "source": "https://github.com/xoraus/CrackingTheSQLInterview",
        "license": "MIT, Copyright (c) 2019 Sajjad Salaria",
        "questions": sorted(qs, key=lambda q: q["number"]),
    })


# ------------------------------------------------- Behavioral questions (MIT)
def behavioral() -> None:
    path = "yangshun/tech-interview-handbook/main/apps/website/contents/behavioral-interview-questions.md"
    text = fetch(path)
    sections, cur = [], None
    for ln in text.split("\n"):
        m = re.match(r"^## (.+)$", ln)
        if m:
            title = m.group(1).replace(" Software Engineer behavioral interview questions", "").strip()
            if title.startswith("Most commonly asked"):
                title = "Most common (all companies)"
            cur = {"title": title, "questions": []}
            sections.append(cur)
            continue
        q = re.match(r"^\s*(?:\d+\.|-)\s+(.+)$", ln)
        if cur is not None and q:
            cur["questions"].append(re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", q.group(1)).strip())
    sections = [s for s in sections if s["questions"]]
    write("behavioral.json", {
        "source": "https://www.techinterviewhandbook.org/behavioral-interview-questions/",
        "repo": "https://github.com/yangshun/tech-interview-handbook",
        "license": "MIT, Copyright (c) Yangshun Tay",
        "sections": sections,
    })


# ------------------------------------------- Algorithm templates (MIT)
TEMPLATES = [
    ("Binary search", "searches/binary_search.py", "binary-search"),
    ("Quick sort", "sorts/quick_sort.py", "sorting"),
    ("Merge sort", "sorts/merge_sort.py", "sorting"),
    ("Breadth-first search", "graphs/breadth_first_search.py", "breadth-first-search"),
    ("Depth-first search", "graphs/depth_first_search.py", "depth-first-search"),
    ("Dijkstra's shortest path", "graphs/dijkstra.py", "shortest-path"),
    ("Union-Find (disjoint set)", "data_structures/disjoint_set/disjoint_set.py", "union-find"),
    ("Trie", "data_structures/trie/trie.py", "trie"),
    ("0/1 Knapsack", "dynamic_programming/knapsack.py", "dynamic-programming"),
    ("Knuth-Morris-Pratt string search", "strings/knuth_morris_pratt.py", "string-matching"),
    ("Binary search tree", "data_structures/binary_tree/binary_search_tree.py", "binary-search-tree"),
]


def templates() -> None:
    out = []
    for title, path, tag in TEMPLATES:
        out.append({
            "title": title,
            "tag": tag,
            "url": f"https://github.com/TheAlgorithms/Python/blob/master/{path}",
            "code": fetch(f"TheAlgorithms/Python/master/{path}"),
        })
    write("templates.json", {
        "source": "https://github.com/TheAlgorithms/Python",
        "license": "MIT, Copyright (c) 2016-present TheAlgorithms and contributors",
        "templates": out,
    })


# ------------------------------------ System design: titles + links only
def system_design() -> None:
    primer = fetch("donnemartin/system-design-primer/master/README.md")
    keep = [
        "Performance vs scalability", "Latency vs throughput", "Availability vs consistency", "Consistency patterns",
        "Availability patterns", "Domain name system", "Content delivery network", "Load balancer",
        "Reverse proxy (web server)", "Application layer", "Database", "Cache", "Asynchronism", "Communication",
        "Security", "How to approach a system design interview question",
        "System design interview questions with solutions",
    ]
    headings = {m.group(1).strip() for m in re.finditer(r"^## (.+)$", primer, re.M)}
    primer_topics = [
        {"title": t, "url": f"https://github.com/donnemartin/system-design-primer#{gh_anchor(t)}"}
        for t in keep if t in headings
    ]
    karan = fetch("karanpratapsingh/system-design/main/README.md")
    chapters = []
    for m in re.finditer(r"^# (.+)$", karan, re.M):
        title = m.group(1).strip()
        if title in ("System Design", "Table of contents"):
            continue
        chapters.append({"title": title, "url": f"https://github.com/karanpratapsingh/system-design#{gh_anchor(title)}"})
    write("system_design.json", {
        "primer": {
            "source": "https://github.com/donnemartin/system-design-primer",
            "license": "CC BY 4.0 (links and titles only; summaries are our own)",
            "topics": primer_topics,
        },
        "karan": {
            "source": "https://github.com/karanpratapsingh/system-design",
            "license": "CC BY-NC-ND 4.0 (titles and outbound links only, no content copied)",
            "chapters": chapters,
        },
    })


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for step in (neetcode, sql_qa, behavioral, templates, system_design):
        step()


if __name__ == "__main__":
    main()
