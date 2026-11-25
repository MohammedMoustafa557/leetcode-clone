def test_list_all(client):
    r = client.get("/api/problems")
    body = r.json()
    assert r.status_code == 200
    assert body["total"] == 6
    ids = [p["frontend_id"] for p in body["items"]]
    assert ids == sorted(ids)
    assert body["items"][0]["title"] == "Two Sum"
    assert body["items"][0]["company_count"] == 2


def test_filters(client):
    assert client.get("/api/problems", params={"difficulty": "Medium"}).json()["total"] == 1
    linked = client.get("/api/problems", params={"tag": "linked-list"}).json()["items"]
    assert {p["slug"] for p in linked} == {"reverse-linked-list"}
    two = client.get("/api/problems", params={"tag": ["array", "hash-table"]}).json()
    assert [p["slug"] for p in two["items"]] == ["two-sum"]
    assert client.get("/api/problems", params={"q": "paren"}).json()["total"] == 1
    assert client.get("/api/problems", params={"q": "1"}).json()["items"][0]["slug"] == "two-sum"


def test_company_filter_sorted_by_frequency(client):
    r = client.get("/api/problems", params={"company": "google", "sort": "frequency", "order": "desc"}).json()
    assert [p["slug"] for p in r["items"]] == ["two-sum", "number-of-islands"]
    assert r["items"][0]["frequency"] == 100.0


def test_sort_by_difficulty_and_pagination(client):
    r = client.get("/api/problems", params={"sort": "difficulty", "order": "desc", "page_size": 2}).json()
    assert r["items"][0]["difficulty"] == "Medium"
    assert len(r["items"]) == 2 and r["total"] == 6
    page3 = client.get("/api/problems", params={"page": 3, "page_size": 2}).json()
    assert len(page3["items"]) == 2


def test_detail_and_solution(client):
    p = client.get("/api/problems/two-sum").json()
    assert p["entry_point"] == "Solution().twoSum"
    assert p["test_count"] == 12
    assert p["heavy_tests"] is False
    assert "class Solution" in p["starter_code"]
    assert p["companies"][0] == {"name": "Google", "slug": "google", "frequency": 100.0, "recency": "30d"}
    assert {t["slug"] for t in p["tags"]} == {"array", "hash-table"}
    assert "def twoSum" in client.get("/api/problems/two-sum/solution").json()["solution"]
    assert client.get("/api/problems/nope").status_code == 404


def test_tags_companies_random(client):
    tags = client.get("/api/tags").json()
    assert tags[0]["count"] >= tags[-1]["count"]
    companies = {c["slug"]: c["count"] for c in client.get("/api/companies").json()}
    assert companies == {"google": 2, "amazon": 2}
    assert client.get("/api/problems/random", params={"difficulty": "Easy"}).json()["difficulty"] == "Easy"


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}
