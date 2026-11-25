"""Judge harness shared by the browser runner (Pyodide) and the CPython tests.

The harness receives:
  * ``preamble``    - imports + helpers (ListNode, TreeNode, ...) that LeetCode
                      problems expect to exist,
  * ``user_code``   - the code typed by the user,
  * ``entry_point`` - expression that yields the callable, e.g. ``Solution().twoSum``,
  * ``test_code``   - a ``def check(candidate):`` function whose body is one
                      ``assert`` per line (LeetCodeDataset format),
  * ``limit``       - optional max number of test cases to run (``Run`` uses the
                      first few cases as public examples, ``Submit`` runs all).

It returns a JSON-serialisable dict with the verdict and per-case details.
Verdicts: Accepted, Wrong Answer, Runtime Error, Compile Error.
(Time Limit Exceeded is decided by the caller, which kills the worker.)
"""

from __future__ import annotations

import ast
import io
import sys
import time
import traceback
from contextlib import redirect_stdout

MAX_REPR = 300
MAX_STDOUT = 4000


def _short(value: object) -> str:
    try:
        text = repr(value)
    except Exception:  # pragma: no cover - exotic objects
        text = "<unrepresentable>"
    return text if len(text) <= MAX_REPR else text[: MAX_REPR - 3] + "..."


def parse_cases(test_code: str) -> list[dict]:
    """Split ``check(candidate)`` into one entry per assert statement."""
    tree = ast.parse(test_code)
    check = next(
        (n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "check"),
        None,
    )
    if check is None:
        raise ValueError("test code has no check() function")
    cases = []
    for node in check.body:
        if not isinstance(node, ast.Assert):
            continue
        case = {"source": ast.unparse(node.test), "actual": None, "expected": None}
        test = node.test
        if (
            isinstance(test, ast.Compare)
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Eq)
        ):
            case["actual"] = ast.unparse(test.left)
            case["expected"] = ast.unparse(test.comparators[0])
        cases.append(case)
    return cases


def _input_label(expr: str) -> str:
    """``candidate(nums = [1], target = 2)`` -> ``nums = [1], target = 2``."""
    for prefix in ("candidate(",):
        start = expr.find(prefix)
        if start != -1 and expr.endswith(")"):
            return expr[start + len(prefix) : -1]
    return expr


def run(
    preamble: str,
    user_code: str,
    entry_point: str,
    test_code: str,
    limit: int | None = None,
) -> dict:
    started = time.perf_counter()
    stdout = io.StringIO()
    env: dict = {"__name__": "__solution__"}
    result: dict = {"verdict": "Accepted", "passed": 0, "total": 0, "cases": []}

    try:
        cases = parse_cases(test_code)
    except Exception as exc:  # broken dataset entry, should not happen
        return {**result, "verdict": "Runtime Error", "error": f"Bad test code: {exc}"}
    if limit is not None:
        cases = cases[:limit]
    result["total"] = len(cases)

    # 1) compile + define the solution
    try:
        exec(compile(preamble, "<preamble>", "exec"), env)
        compiled = compile(user_code, "solution.py", "exec")
    except SyntaxError as exc:
        return {
            **result,
            "verdict": "Compile Error",
            "error": f"SyntaxError: {exc.msg} (line {exc.lineno})",
        }
    try:
        with redirect_stdout(stdout):
            exec(compiled, env)
    except Exception:
        return {**result, "verdict": "Runtime Error", "error": _tb()}

    # 2) run each assert as its own case
    for index, case in enumerate(cases):
        detail = {"index": index, "input": _input_label(case["actual"] or case["source"])}
        try:
            with redirect_stdout(stdout):
                # fresh instance per case, like LeetCode
                candidate = eval(entry_point, env)
                env["candidate"] = candidate
                if case["actual"] is not None:
                    actual = eval(case["actual"], env)
                    expected = eval(case["expected"], env)
                    ok = actual == expected
                    detail["output"] = _short(actual)
                    detail["expected"] = _short(expected)
                else:
                    ok = bool(eval(case["source"], env))
        except Exception:
            detail["error"] = _tb()
            result["cases"].append(detail)
            result["verdict"] = "Runtime Error"
            result["error"] = detail["error"]
            break
        detail["passed"] = ok
        result["cases"].append(detail)
        if not ok:
            result["verdict"] = "Wrong Answer"
            break
        result["passed"] += 1

    result["runtime_ms"] = round((time.perf_counter() - started) * 1000, 1)
    out = stdout.getvalue()
    result["stdout"] = out[:MAX_STDOUT]
    return result


def _tb() -> str:
    etype, value, tb = sys.exc_info()
    frames = [
        f for f in traceback.extract_tb(tb) if f.filename == "solution.py"
    ]
    where = f" (line {frames[-1].lineno})" if frames else ""
    return f"{etype.__name__}: {value}{where}"
