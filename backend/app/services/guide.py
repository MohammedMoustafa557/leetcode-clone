"""Per-problem study guide.

Without an LLM key everything is *derived* from the problem's tags and an AST scan
of the reference solution - nothing is invented. With LLM_API_KEY set, an
OpenAI-compatible model writes a richer guide; results are cached in the DB.
"""

from __future__ import annotations

import ast
import json
import logging

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Problem, ProblemGuide

log = logging.getLogger(__name__)

# technique -> (English name, Arabic name, hint)
TECHNIQUES: dict[str, tuple[str, str, str]] = {
    "hash": ("a hash map", "هاش ماب (قاموس)", "Can you remember what you have already seen in a dictionary/set for O(1) lookups?"),
    "two_pointers": ("two pointers", "مؤشرين", "Try two indexes that move toward each other (or both forward) instead of a nested loop."),
    "sliding_window": ("a sliding window", "نافذة منزلقة", "Keep a window [left, right] and shrink it from the left when it becomes invalid."),
    "sort": ("sorting", "الترتيب", "Would sorting the input first make the problem easier?"),
    "heap": ("a heap (priority queue)", "هيب (طابور أولوية)", "You often need the smallest/largest item quickly - a heap gives it in O(log n)."),
    "bfs": ("breadth-first search", "البحث بالعرض (BFS)", "Explore level by level with a queue (collections.deque)."),
    "dfs": ("depth-first search / recursion", "البحث بالعمق (DFS) والاستدعاء الذاتي", "Solve the problem for smaller parts (children/neighbours) recursively and combine the answers."),
    "dp": ("dynamic programming", "البرمجة الديناميكية", "Define what dp[i] means, how it depends on smaller states, and the base case."),
    "binary_search": ("binary search", "البحث الثنائي", "Is there something sorted or monotonic you can cut in half each step?"),
    "stack": ("a stack", "ستاك (مكدس)", "Process items in order and keep the 'open' ones on a stack."),
    "union_find": ("union-find", "يونيون فايند (المجموعات المنفصلة)", "Merge connected items into groups and ask which group each belongs to."),
    "greedy": ("a greedy choice", "اختيار جشع", "Is there a locally best choice at each step that is always safe?"),
    "bit": ("bit manipulation", "التلاعب بالبتات", "Think about the binary form of the numbers: XOR, AND, shifts."),
    "linked_list": ("pointer manipulation on the linked list", "التعامل مع مؤشرات القائمة المرتبطة", "Draw the nodes and arrows; keep track of prev/cur/next."),
    "math": ("math", "الرياضيات", "Look for a formula or a property of the numbers instead of brute force."),
    "simulation": ("a direct simulation", "محاكاة مباشرة", "Follow the rules of the problem step by step; watch the edge cases."),
}

TAG_TO_TECH = {
    "hash-table": "hash", "two-pointers": "two_pointers", "sliding-window": "sliding_window", "sorting": "sort",
    "heap-priority-queue": "heap", "breadth-first-search": "bfs", "depth-first-search": "dfs",
    "dynamic-programming": "dp", "binary-search": "binary_search", "stack": "stack", "monotonic-stack": "stack",
    "union-find": "union_find", "greedy": "greedy", "bit-manipulation": "bit", "linked-list": "linked_list",
    "math": "math", "simulation": "simulation", "recursion": "dfs", "backtracking": "dfs", "memoization": "dp",
}


class _Scan(ast.NodeVisitor):
    def __init__(self) -> None:
        self.found: list[str] = []
        self.max_loop_depth = 0
        self._depth = 0
        self.funcs: set[str] = set()
        self.recursive = False

    def add(self, t: str) -> None:
        if t not in self.found:
            self.found.append(t)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.funcs.add(node.name)
        for d in node.decorator_list:
            name = ast.unparse(d)
            if "cache" in name:
                self.add("dp")
        self.generic_visit(node)

    def _loop(self, node: ast.AST) -> None:
        self._depth += 1
        self.max_loop_depth = max(self.max_loop_depth, self._depth)
        self.generic_visit(node)
        self._depth -= 1

    visit_For = _loop
    visit_While = _loop

    def visit_Call(self, node: ast.Call) -> None:
        name = ast.unparse(node.func)
        if name.split(".")[-1] in self.funcs:
            self.recursive = True
        if any(k in name for k in ("heappush", "heappop", "heapify", "nlargest", "nsmallest")):
            self.add("heap")
        elif "bisect" in name:
            self.add("binary_search")
        elif name.endswith("sort") or name == "sorted":
            self.add("sort")
        elif name in ("deque", "collections.deque"):
            self.add("bfs")
        elif name in ("Counter", "defaultdict", "dict", "set") or name.endswith((".get", ".setdefault")):
            self.add("hash")
        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict) -> None:
        self.add("hash")
        self.generic_visit(node)


def scan_solution(code: str) -> _Scan:
    s = _Scan()
    try:
        s.visit(ast.parse(code))
    except SyntaxError:
        pass
    if s.recursive:
        s.add("dfs")
    return s


def estimate_complexity(scan: _Scan) -> tuple[str, str]:
    if "dp" in scan.found:
        time = "O(number of states × work per state)"
    elif scan.max_loop_depth >= 3:
        time = "O(n³)"
    elif scan.max_loop_depth == 2:
        time = "O(n²) in the worst case (often less with early exits)"
    elif "sort" in scan.found:
        time = "O(n log n)"
    elif "heap" in scan.found:
        time = "O(n log n) (or O(n log k) with a size-k heap)"
    elif "binary_search" in scan.found and scan.max_loop_depth <= 1:
        time = "O(log n) per search"
    elif scan.max_loop_depth == 1 or scan.recursive:
        time = "O(n)"
    else:
        time = "O(1)"
    space = "O(n)" if any(t in scan.found for t in ("hash", "dp", "heap", "bfs", "dfs")) else "O(1) extra"
    return time, space


def auto_guide(p: Problem) -> dict:
    tag_slugs = [t.slug for t in p.tags]
    scan = scan_solution(p.solution or "")
    techs: list[str] = []
    for t in scan.found + [TAG_TO_TECH[s] for s in tag_slugs if s in TAG_TO_TECH]:
        if t not in techs:
            techs.append(t)
    if not techs:
        techs = ["simulation"]
    main = techs[0]
    en, ar, hint = TECHNIQUES[main]
    others = [TECHNIQUES[t][0] for t in techs[1:3]]
    time, space = estimate_complexity(scan)
    topic_list = ", ".join(t.name for t in p.tags) or "general problem solving"

    hints = [
        f"Topics: {topic_list}. Start with a brute-force idea and say its complexity out loud.",
        hint,
        f"The reference solution is built around {en}"
        + (f", together with {' and '.join(others)}" if others else "")
        + f". Aim for {time.split(' (')[0]} time.",
    ]
    explanation = (
        f"Main idea: use {en}. "
        + (f"It also uses {' and '.join(others)}. " if others else "")
        + "First handle the simple edge cases (empty input, one element), then apply the idea in one clean pass."
    )
    sentences = [
        {"en": f"Let me make sure I understand: we need to solve \"{p.title}\", right?",
         "ar": f"خليني أتأكد إني فاهم: إحنا محتاجين نحل \"{p.title}\"، صح؟"},
        {"en": "First, I will explain a simple brute-force solution, and then I will improve it.",
         "ar": "الأول هشرح حل بسيط (brute force)، وبعدين هحسنه."},
        {"en": f"I think {en} is a good fit here.",
         "ar": f"أعتقد إن {ar} مناسب هنا."},
        {"en": f"The time complexity is {time.split(' (')[0]} and the space complexity is {space}.",
         "ar": f"التعقيد الزمني {time.split(' (')[0]} والتعقيد المكاني {space}."},
        {"en": "Let me test my code with the example and one edge case.",
         "ar": "خليني أجرب الكود على المثال وعلى حالة طرفية."},
    ]
    return {
        "source": "auto",
        "hints": hints,
        "explanation": explanation,
        "time_complexity": time,
        "space_complexity": space,
        "complexity_note": "Estimated automatically from the reference solution's structure - verify it yourself.",
        "techniques": [TECHNIQUES[t][0] for t in techs],
        "interview_sentences": sentences,
    }


LLM_PROMPT = """You are a coding interview coach for an Arabic-speaking learner (English level A2).
Return ONLY a JSON object with keys:
"hints": 3 progressive hints (first vague, last almost the approach, never full code),
"explanation": a simple-English explanation of the optimal approach (max 120 words),
"time_complexity", "space_complexity": Big-O strings,
"interview_sentences": 5 objects {"en": sentence to say in the interview, "ar": Egyptian Arabic translation}.

Problem: {title} ({difficulty}); tags: {tags}
Statement:
{description}

Reference solution:
{solution}
"""


def llm_guide(p: Problem) -> dict | None:
    s = get_settings()
    if not s.llm_api_key:
        return None
    fields = {
        "{title}": p.title, "{difficulty}": p.difficulty, "{tags}": ", ".join(t.name for t in p.tags),
        "{description}": p.description[:4000], "{solution}": (p.solution or "")[:3000],
    }
    prompt = LLM_PROMPT
    for k, v in fields.items():
        prompt = prompt.replace(k, v)
    try:
        r = httpx.post(
            f"{s.llm_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {s.llm_api_key}"},
            json={"model": s.llm_model, "messages": [{"role": "user", "content": prompt}],
                  "response_format": {"type": "json_object"}, "temperature": 0.2},
            timeout=60,
        )
        r.raise_for_status()
        data = json.loads(r.json()["choices"][0]["message"]["content"])
        if len(data.get("hints", [])) < 3 or len(data.get("interview_sentences", [])) < 5:
            return None
        data["source"] = "llm"
        data["complexity_note"] = f"Written by {s.llm_model}; double-check it."
        data.setdefault("techniques", [])
        return data
    except Exception as exc:  # network/format problems fall back to the auto guide
        log.warning("LLM guide failed for %s: %s", p.slug, exc)
        return None


def get_guide(db: Session, p: Problem) -> dict:
    cached = db.get(ProblemGuide, p.id)
    want_llm = bool(get_settings().llm_api_key)
    if cached and (cached.source == "llm" or not want_llm):
        return json.loads(cached.data)
    data = llm_guide(p) or auto_guide(p)
    if cached:
        cached.source, cached.data = data["source"], json.dumps(data, ensure_ascii=False)
    else:
        db.add(ProblemGuide(problem_id=p.id, source=data["source"], data=json.dumps(data, ensure_ascii=False)))
    db.commit()
    return data
