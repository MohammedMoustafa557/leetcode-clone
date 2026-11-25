from datetime import date, timedelta

from app.services.progress import streaks


def submit(client, auth, slug="two-sum", verdict="Accepted", passed=12, total=12):
    return client.post(
        "/api/submissions",
        headers=auth,
        json={"problem_slug": slug, "code": "class Solution: ...", "verdict": verdict,
              "passed": passed, "total": total, "runtime_ms": 12.5},
    )


def test_submit_and_progress(client, auth):
    assert submit(client, auth, verdict="Wrong Answer", passed=3).status_code == 201
    assert client.get("/api/problems/two-sum", headers=auth).json()["status"] == "attempted"
    assert submit(client, auth).status_code == 201
    assert client.get("/api/problems/two-sum", headers=auth).json()["status"] == "solved"
    assert submit(client, auth, slug="valid-parentheses", verdict="Runtime Error", passed=0).status_code == 201

    solved = client.get("/api/problems", params={"status": "solved"}, headers=auth).json()
    assert [p["slug"] for p in solved["items"]] == ["two-sum"]
    todo = client.get("/api/problems", params={"status": "todo"}, headers=auth).json()
    assert todo["total"] == 4

    stats = client.get("/api/me/stats", headers=auth).json()
    assert stats["solved"] == 1 and stats["attempted"] == 1
    assert stats["submissions"] == 3
    assert stats["acceptance_rate"] == 33.3
    assert stats["by_difficulty"]["Easy"] == {"solved": 1, "total": 5}
    assert stats["streak"] == 1
    assert sum(stats["calendar"].values()) == 3

    history = client.get("/api/submissions", params={"problem_slug": "two-sum"}, headers=auth).json()
    assert [h["verdict"] for h in history] == ["Accepted", "Wrong Answer"]
    one = client.get(f"/api/submissions/{history[0]['id']}", headers=auth).json()
    assert one["code"] == "class Solution: ..."


def test_submission_validation(client, auth):
    assert submit(client, auth, passed=11).status_code == 422  # Accepted but not all passed
    assert submit(client, auth, verdict="Wrong Answer", passed=13, total=12).status_code == 422
    assert submit(client, auth, slug="missing").status_code == 404
    assert submit(client, auth, verdict="Hacked").status_code == 422


def test_submissions_are_private(client, auth):
    from tests.conftest import register

    sub_id = submit(client, auth).json()["id"]
    other = register(client, username="other")
    assert client.get(f"/api/submissions/{sub_id}", headers=other).status_code == 404
    assert client.get("/api/submissions", headers=other).json() == []


def test_streaks():
    today = date(2026, 11, 25)
    d = lambda n: today - timedelta(days=n)  # noqa: E731
    assert streaks(set(), today) == (0, 0)
    assert streaks({d(0), d(1), d(2)}, today) == (3, 3)
    assert streaks({d(1), d(2)}, today) == (2, 2)  # yesterday still counts
    assert streaks({d(2), d(3)}, today) == (0, 2)
    assert streaks({d(0), d(5), d(6), d(7), d(8)}, today) == (1, 4)
