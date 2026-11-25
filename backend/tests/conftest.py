import json
import os
import sys
import tempfile
from pathlib import Path

_DEFAULT_DB = "sqlite:///" + os.path.join(tempfile.gettempdir(), "codearena_test.db")
# Tests run on SQLite by default; set TEST_DATABASE_URL to run them against PostgreSQL.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", _DEFAULT_DB)
os.environ["JWT_SECRET"] = "test-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from scripts.seed import seed  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runner"))

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = json.loads((FIXTURES / "sample_problems.json").read_text())
COMPANIES = {
    "Google": {"two-sum": (100.0, "30d", "Two Sum"), "number-of-islands": (80.0, "3m", "Number of Islands")},
    "Amazon": {"two-sum": (90.0, "6m", "Two Sum"), "valid-parentheses": (70.0, "6m+", "Valid Parentheses")},
}


@pytest.fixture(autouse=True)
def db_setup():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db, SAMPLE, COMPANIES)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample():
    return {r["task_id"]: r for r in SAMPLE}


def register(client, username="mohammed", password="supersecret1"):
    r = client.post(
        "/api/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": password},
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def auth(client):
    return register(client)
