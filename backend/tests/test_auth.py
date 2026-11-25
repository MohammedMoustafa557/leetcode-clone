from tests.conftest import register


def test_register_login_me(client):
    headers = register(client)
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["username"] == "mohammed"

    for login in ("mohammed", "MOHAMMED@example.com"):
        r = client.post("/api/auth/login", json={"login": login, "password": "supersecret1"})
        assert r.status_code == 200
        assert r.json()["token_type"] == "bearer"


def test_oauth2_token_form(client):
    register(client)
    r = client.post("/api/auth/token", data={"username": "mohammed", "password": "supersecret1"})
    assert r.status_code == 200 and r.json()["access_token"]


def test_password_is_hashed(client):
    from app.db import SessionLocal
    from app.models import User

    register(client)
    with SessionLocal() as db:
        user = db.query(User).one()
        assert user.password_hash != "supersecret1"
        assert user.password_hash.startswith("$2")


def test_duplicate_and_bad_credentials(client):
    register(client)
    dup = client.post(
        "/api/auth/register",
        json={"username": "Mohammed", "email": "x@example.com", "password": "supersecret1"},
    )
    assert dup.status_code == 409
    bad = client.post("/api/auth/login", json={"login": "mohammed", "password": "wrongpass"})
    assert bad.status_code == 401


def test_validation(client):
    r = client.post("/api/auth/register", json={"username": "ab", "email": "nope", "password": "123"})
    assert r.status_code == 422


def test_protected_routes_need_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/me/stats").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
