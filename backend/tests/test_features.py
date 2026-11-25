from datetime import UTC, datetime, timedelta

import pytest

from app.services import clock, community, guide, plans
from tests.conftest import register
from tests.test_submissions import submit


class Clock:
    def __init__(self, t: datetime):
        self.t = t

    def __call__(self) -> datetime:
        return self.t


@pytest.fixture
def frozen(monkeypatch):
    c = Clock(datetime(2026, 11, 27, 12, 0, tzinfo=UTC))
    monkeypatch.setattr(clock, "now", c)
    return c


# ---------------------------------------------------------------- plans & daily
def test_plans_only_include_catalog_problems(client, auth):
    plans_ = {p["id"]: p for p in client.get("/api/plans").json()}
    assert set(plans_) == {"blind75", "neetcode", "striver"}
    assert plans_["blind75"]["upstream_total"] == 75
    assert plans_["neetcode"]["upstream_total"] == 450
    assert plans_["blind75"]["matched"] == 6  # every fixture problem is a Blind 75 problem
    submit(client, auth)
    detail = client.get("/api/plans/blind75", headers=auth).json()
    names = [g["name"] for g in detail["groups"]]
    assert names == sorted(names, key=plans.NEETCODE_ORDER.index)
    flat = {p["slug"]: p["status"] for g in detail["groups"] for p in g["problems"]}
    assert flat["two-sum"] == "solved" and flat["valid-parentheses"] == "todo"
    assert client.get("/api/plans/nope").status_code == 404


def test_daily_is_deterministic_and_rotates(client, frozen):
    a = client.get("/api/daily").json()
    assert a["date"] == "2026-11-27" and a["problem"]["difficulty"] != "Hard"
    assert client.get("/api/daily").json() == a
    groups = set()
    for d in range(10):
        frozen.t = datetime(2026, 12, 1, tzinfo=UTC) + timedelta(days=d)
        groups.add(client.get("/api/daily").json()["group"])
    assert len(groups) > 1


# ---------------------------------------------------------------- guide
def test_auto_guide_is_derived_and_cached(client):
    g = client.get("/api/problems/two-sum/guide").json()
    assert g["source"] == "auto"
    assert len(g["hints"]) == 3 and len(g["interview_sentences"]) == 5
    assert all(s["en"] and s["ar"] for s in g["interview_sentences"])
    assert "hash map" in g["techniques"][0]
    assert "Estimated" in g["complexity_note"]
    assert client.get("/api/problems/two-sum/guide").json() == g
    assert client.get("/api/problems/nope/guide").status_code == 404


def test_complexity_estimates():
    s = guide.scan_solution("class S:\n  def f(self, a):\n    for i in a:\n      for j in a:\n        pass\n")
    assert guide.estimate_complexity(s)[0].startswith("O(n²)")
    s = guide.scan_solution("class S:\n  def f(self, a):\n    a.sort()\n    return a\n")
    assert guide.estimate_complexity(s)[0] == "O(n log n)"


def test_llm_guide_used_when_key_set(client, monkeypatch):
    from app.core import config

    settings = config.get_settings()
    monkeypatch.setattr(settings, "llm_api_key", "x")

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            import json
            body = {"hints": ["a", "b", "c"], "explanation": "e", "time_complexity": "O(n)",
                    "space_complexity": "O(n)", "interview_sentences": [{"en": "hi", "ar": "اهلا"}] * 5}
            return {"choices": [{"message": {"content": json.dumps(body)}}]}

    monkeypatch.setattr(guide.httpx, "post", lambda *a, **k: Resp())
    g = client.get("/api/problems/climbing-stairs/guide").json()
    assert g["source"] == "llm" and g["hints"] == ["a", "b", "c"]


# ---------------------------------------------------------------- learn
def test_learn_content(client):
    pats = client.get("/api/learn/patterns").json()
    assert len(pats) == 16
    assert any(p["problems"] for p in pats)
    assert len(client.get("/api/learn/sql").json()["questions"]) == 115
    assert len(client.get("/api/learn/templates").json()["templates"]) == 11
    beh = client.get("/api/learn/behavioral").json()
    assert sum(len(s["questions"]) for s in beh["sections"]) >= 100
    sd = client.get("/api/learn/system-design").json()
    assert sd["karan"]["chapters"] and all("content" not in c for c in sd["karan"]["chapters"])


# ---------------------------------------------------------------- interviews
def test_interview_flow(client, auth, frozen):
    assert client.post("/api/interviews", json={"company_slug": "nope"}, headers=auth).status_code == 404
    r = client.post("/api/interviews", json={"company_slug": "google"}, headers=auth)
    assert r.status_code == 201
    s = r.json()
    assert s["seconds_left"] == 45 * 60 and len(s["problems"]) == 2
    assert {p["slug"] for p in s["problems"]} == {"two-sum", "number-of-islands"}
    frozen.t += timedelta(minutes=10)
    assert submit(client, auth, slug="two-sum").status_code == 201
    assert submit(client, auth, slug="number-of-islands").status_code == 201
    frozen.t += timedelta(minutes=5)
    done = client.post(f"/api/interviews/{s['id']}/finish", headers=auth).json()
    assert all(p["solved"] for p in done["problems"])
    assert done["score"] == 80 + round(20 * (1 - 15 / 45))
    other = register(client, "someone")
    assert client.get(f"/api/interviews/{s['id']}", headers=other).status_code == 404
    assert len(client.get("/api/interviews", headers=auth).json()) == 1


# ---------------------------------------------------------------- stats
def test_tag_stats(client, auth):
    submit(client, auth, verdict="Wrong Answer", passed=1)
    submit(client, auth)
    submit(client, auth, slug="climbing-stairs", verdict="Wrong Answer", passed=0)
    submit(client, auth, slug="climbing-stairs", verdict="Wrong Answer", passed=0)
    stats = client.get("/api/me/stats", headers=auth).json()
    by = {t["slug"]: t for t in stats["tag_stats"]}
    assert by["hash-table"]["solved"] == 1 and by["hash-table"]["accuracy"] == 50.0
    assert stats["weaknesses"][0]["accuracy"] == 0.0


# ---------------------------------------------------------------- community
def test_profile_badges_leaderboard(client, auth):
    submit(client, auth)  # Easy
    submit(client, auth, slug="number-of-islands")  # Medium
    b = register(client, "bob")
    submit(client, b, slug="climbing-stairs")
    prof = client.get("/api/users/mohammed").json()
    assert prof["solved"] == {"Easy": 1, "Medium": 1, "Hard": 0}
    assert prof["points"] == 30 and prof["rating"] == 1500 and prof["global_rank"] is None
    assert {x["id"]: x["earned"] for x in prof["badges"]}["first-solve"]
    assert "email" not in prof
    board = client.get("/api/leaderboard").json()
    assert [r["username"] for r in board] == ["mohammed", "bob"]
    assert board[0]["rank"] == 1
    assert client.get("/api/users/ghost").status_code == 404


def test_elo_math():
    assert community.elo_deltas([1500], [1]) == [0]
    d = community.elo_deltas([1500, 1500], [1, 2])
    assert d[0] > 0 and d[0] == -d[1]
    up_strong, up_weak = community.elo_deltas([1800, 1400], [1, 2])
    upset = community.elo_deltas([1800, 1400], [2, 1])
    assert upset[1] > up_weak * -1 > 0 or upset[1] > 0
    assert abs(upset[0]) > abs(up_strong)


def test_weekly_contest_end_to_end(client, auth, frozen):
    cur = client.get("/api/contests/current").json()
    start = datetime.fromisoformat(cur["starts_at"])
    assert cur["phase"] == "upcoming" and cur["problems"] == []
    assert start.weekday() == 4  # Friday
    bob = register(client, "bob")
    n = cur["number"]
    assert client.post(f"/api/contests/{n}/register", headers=auth).status_code == 201
    assert client.post(f"/api/contests/{n}/register", headers=bob).json()["registered"]

    frozen.t = start + timedelta(minutes=5)
    live = client.get(f"/api/contests/{n}", headers=auth).json()
    assert live["phase"] == "running" and len(live["problems"]) == 4
    q1 = live["problems"][0]["slug"]
    submit(client, auth, slug=q1)
    frozen.t = start + timedelta(minutes=20)
    submit(client, bob, slug=q1, verdict="Wrong Answer", passed=0)
    submit(client, bob, slug=q1)
    live = client.get(f"/api/contests/{n}", headers=auth).json()
    assert live["problems"][0]["solved"]
    assert [s["username"] for s in live["standings"]] == ["mohammed", "bob"]

    frozen.t = start + timedelta(hours=3)
    final = client.get(f"/api/contests/{n}").json()
    assert final["rated"] and final["phase"] == "finished"
    top, second = final["standings"]
    assert top["rank"] == 1 and top["rating_after"] > 1500 > second["rating_after"]
    assert top["penalty_seconds"] == 5 * 60 and second["penalty_seconds"] == 20 * 60 + 5 * 60
    assert client.post(f"/api/contests/{n}/register", headers=auth).status_code == 409
    prof = client.get("/api/users/mohammed").json()
    assert prof["global_rank"] == 1 and prof["contest_history"][0]["rank"] == 1
    assert {x["id"]: x["earned"] for x in prof["badges"]}["contest-1"]
    # finalization is idempotent
    assert client.get(f"/api/contests/{n}").json()["standings"] == final["standings"]


def test_submissions_outside_window_do_not_count(client, auth, frozen):
    cur = client.get("/api/contests/current").json()
    n = cur["number"]
    client.post(f"/api/contests/{n}/register", headers=auth)
    frozen.t = datetime.fromisoformat(cur["starts_at"]) + timedelta(minutes=1)
    slug = client.get(f"/api/contests/{n}").json()["problems"][0]["slug"]
    frozen.t = datetime.fromisoformat(cur["ends_at"]) + timedelta(minutes=1)
    submit(client, auth, slug=slug)
    assert client.get(f"/api/contests/{n}", headers=auth).json()["standings"][0]["score"] == 0
