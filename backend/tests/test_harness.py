"""The judge harness (runner/harness.py) is the exact code the browser runs in Pyodide."""

import harness
import pytest

WRONG = {
    "two-sum": "class Solution:\n    def twoSum(self, nums, target):\n        return [0, 1]\n",
    "valid-parentheses": "class Solution:\n    def isValid(self, s):\n        return len(s) % 2 == 0\n",
    "reverse-linked-list": "class Solution:\n    def reverseList(self, head):\n        return head\n",
    "maximum-depth-of-binary-tree": "class Solution:\n    def maxDepth(self, root):\n        return 1 if root else 0\n",
    "climbing-stairs": "class Solution:\n    def climbStairs(self, n):\n        return n\n",
    "number-of-islands": "class Solution:\n    def numIslands(self, grid):\n        return 1\n",
}


def judge(problem, code, limit=None):
    return harness.run(problem["prompt"], code, problem["entry_point"], problem["test"], limit)


@pytest.mark.parametrize("slug", sorted(WRONG))
def test_reference_solution_is_accepted(sample, slug):
    res = judge(sample[slug], sample[slug]["completion"])
    assert res["verdict"] == "Accepted", res
    assert res["passed"] == res["total"] == 12


@pytest.mark.parametrize("slug", sorted(WRONG))
def test_wrong_solution_is_rejected(sample, slug):
    res = judge(sample[slug], WRONG[slug])
    assert res["verdict"] == "Wrong Answer", res
    assert res["passed"] < res["total"]
    failed = res["cases"][-1]
    assert failed["passed"] is False and failed["input"]


def test_wrong_answer_shows_expected_and_output(sample):
    res = judge(sample["two-sum"], WRONG["two-sum"])
    case = res["cases"][-1]
    assert case["output"] == "[0, 1]" and case["expected"] != case["output"]


def test_runtime_and_compile_errors(sample):
    p = sample["two-sum"]
    boom = "class Solution:\n    def twoSum(self, nums, target):\n        return nums[999]\n"
    res = judge(p, boom)
    assert res["verdict"] == "Runtime Error"
    assert "IndexError" in res["error"] and "line 3" in res["error"]
    assert judge(p, "class Solution:\n  def twoSum(self:\n")["verdict"] == "Compile Error"
    assert judge(p, "raise ValueError('x')")["verdict"] == "Runtime Error"


def test_run_limit_and_stdout(sample):
    p = sample["two-sum"]
    code = p["completion"].replace("d = {}", "d = {}\n        print('debug')")
    res = judge(p, code, limit=3)
    assert res["verdict"] == "Accepted" and res["total"] == 3
    assert res["stdout"].count("debug") == 3


def test_parse_cases_non_equality():
    cases = harness.parse_cases("def check(candidate):\n    assert is_same_list(candidate(x=1), list_node([1]))\n")
    assert cases[0]["actual"] is None and "is_same_list" in cases[0]["source"]
