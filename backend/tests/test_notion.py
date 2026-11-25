import httpx

from app.core.config import get_settings
from app.db import SessionLocal
from app.models import NotionSync
from app.services import notion
from tests.test_submissions import submit


def test_notion_off_by_default(client, auth, monkeypatch):
    called = []
    monkeypatch.setattr(notion, "sync_first_solve", lambda *a: called.append(a))
    assert submit(client, auth).status_code == 201
    assert called == []


def test_notion_sync_first_solve(client, auth, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "notion_token", "secret")
    monkeypatch.setattr(s, "notion_database_id", "db1")
    monkeypatch.setattr(s, "notion_sync_username", "mohammed")
    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json={"properties": {
                "Problem": {"type": "title"}, "Difficulty": {"type": "select"}, "Topic": {"type": "select"},
                "Status": {"type": "status"}, "Date": {"type": "date"}, "Time": {"type": "number"}}})
        sent.append(request)
        return httpx.Response(200, json={"id": "page-1"})

    fake = httpx.Client(transport=httpx.MockTransport(handler))
    real = notion.sync_first_solve
    monkeypatch.setattr(notion, "sync_first_solve", lambda u, p: real(u, p, client=fake))
    submit(client, auth)
    submit(client, auth)  # second Accepted: no second page
    assert len(sent) == 1
    import json
    props = json.loads(sent[0].content)["properties"]
    assert props["Problem"]["title"][0]["text"]["content"] == "Two Sum"
    assert props["Difficulty"] == {"select": {"name": "Easy"}}
    assert props["Status"] == {"status": {"name": "Solved"}}
    assert "Time" not in props
    assert sent[0].headers["Authorization"] == "Bearer secret"
    with SessionLocal() as db:
        assert db.query(NotionSync).one().status == "ok"
