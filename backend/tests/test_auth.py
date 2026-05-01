"""Tests for auth endpoints — @Tuo."""

from bson import ObjectId

from backend.app import create_app


class FakeUsersCollection:
    def __init__(self, existing=None):
        self._users = list(existing or [])

    def find_one(self, query):
        for u in self._users:
            if query.get("username") and u.get("username") == query["username"]:
                return dict(u)
            if query.get("_id") and u.get("_id") == query["_id"]:
                return dict(u)
        return None

    def insert_one(self, doc):
        oid = ObjectId()
        doc["_id"] = oid
        self._users.append(doc)

        class R:
            inserted_id = oid

        return R()


def _app():
    return create_app()


def test_register_success(monkeypatch):
    fake = FakeUsersCollection()
    monkeypatch.setattr("backend.auth.get_users_collection", lambda: fake)

    client = _app().test_client()
    resp = client.post("/api/auth/register", json={"username": "alice", "password": "secret"})
    data = resp.get_json()

    assert resp.status_code == 201
    assert data["message"] == "User registered successfully"
    assert "user_id" in data


def test_register_missing_username(monkeypatch):
    fake = FakeUsersCollection()
    monkeypatch.setattr("backend.auth.get_users_collection", lambda: fake)

    client = _app().test_client()
    resp = client.post("/api/auth/register", json={"password": "secret"})

    assert resp.status_code == 400
    assert "Missing required field" in resp.get_json()["error"]


def test_register_missing_password(monkeypatch):
    fake = FakeUsersCollection()
    monkeypatch.setattr("backend.auth.get_users_collection", lambda: fake)

    client = _app().test_client()
    resp = client.post("/api/auth/register", json={"username": "alice"})

    assert resp.status_code == 400


def test_register_duplicate(monkeypatch):
    import bcrypt

    existing = [
        {
            "_id": ObjectId(),
            "username": "alice",
            "password": bcrypt.hashpw(b"secret", bcrypt.gensalt()),
        }
    ]
    fake = FakeUsersCollection(existing)
    monkeypatch.setattr("backend.auth.get_users_collection", lambda: fake)

    client = _app().test_client()
    resp = client.post("/api/auth/register", json={"username": "alice", "password": "other"})

    assert resp.status_code == 409
    assert resp.get_json()["error"] == "Username already exists"


def test_register_bad_json(monkeypatch):
    fake = FakeUsersCollection()
    monkeypatch.setattr("backend.auth.get_users_collection", lambda: fake)

    client = _app().test_client()
    resp = client.post("/api/auth/register", data="not-json", content_type="text/plain")
    assert resp.status_code == 400


def test_login_success(monkeypatch):
    import bcrypt

    uid = ObjectId()
    hashed = bcrypt.hashpw(b"secret", bcrypt.gensalt())
    existing = [{"_id": uid, "username": "alice", "password": hashed}]
    fake = FakeUsersCollection(existing)
    monkeypatch.setattr("backend.auth.get_users_collection", lambda: fake)

    client = _app().test_client()
    resp = client.post("/api/auth/login", json={"username": "alice", "password": "secret"})
    data = resp.get_json()

    assert resp.status_code == 200
    assert "token" in data
    assert data["user_id"] == str(uid)


def test_login_wrong_password(monkeypatch):
    import bcrypt

    hashed = bcrypt.hashpw(b"secret", bcrypt.gensalt())
    existing = [{"_id": ObjectId(), "username": "alice", "password": hashed}]
    fake = FakeUsersCollection(existing)
    monkeypatch.setattr("backend.auth.get_users_collection", lambda: fake)

    client = _app().test_client()
    resp = client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})

    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Invalid credentials"


def test_login_unknown_user(monkeypatch):
    fake = FakeUsersCollection()
    monkeypatch.setattr("backend.auth.get_users_collection", lambda: fake)

    client = _app().test_client()
    resp = client.post("/api/auth/login", json={"username": "ghost", "password": "x"})

    assert resp.status_code == 401


def test_login_missing_fields(monkeypatch):
    fake = FakeUsersCollection()
    monkeypatch.setattr("backend.auth.get_users_collection", lambda: fake)

    client = _app().test_client()
    resp = client.post("/api/auth/login", json={"username": "alice"})

    assert resp.status_code == 400


def test_login_bad_json(monkeypatch):
    fake = FakeUsersCollection()
    monkeypatch.setattr("backend.auth.get_users_collection", lambda: fake)

    client = _app().test_client()
    resp = client.post("/api/auth/login", data="bad", content_type="text/plain")
    assert resp.status_code == 400
