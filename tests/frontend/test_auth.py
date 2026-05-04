import pytest
from unittest.mock import MagicMock
from bson import ObjectId

import db


def _mock_user(username="alice", email="alice@example.com", password=b"hashed"):
    return {"_id": ObjectId(), "username": username, "email": email, "password_hash": password}


# ── GET routes ────────────────────────────────────────────────────────────────

def test_login_get(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"login" in response.data.lower() or b"sign in" in response.data.lower()


def test_register_get(client):
    response = client.get("/register")
    assert response.status_code == 200


# ── POST /register ────────────────────────────────────────────────────────────

def test_register_missing_fields(client):
    response = client.post("/register", data={"username": "", "email": "", "password": ""})
    assert response.status_code == 200
    assert b"required" in response.data.lower()


def test_register_short_password(client):
    db.mongo.db.users.find_one.return_value = None
    response = client.post("/register", data={
        "username": "alice",
        "email": "alice@example.com",
        "password": "abc",
    })
    assert response.status_code == 200
    assert b"6 characters" in response.data.lower() or b"password" in response.data.lower()


def test_register_duplicate_email(client):
    db.mongo.db.users.find_one.return_value = _mock_user()
    response = client.post("/register", data={
        "username": "alice",
        "email": "alice@example.com",
        "password": "password123",
    })
    assert response.status_code == 200
    assert b"already exists" in response.data.lower() or b"email" in response.data.lower()


def test_register_duplicate_username(client):
    # First call (email check) returns None, second (username check) returns a user
    db.mongo.db.users.find_one.side_effect = [None, _mock_user()]
    response = client.post("/register", data={
        "username": "alice",
        "email": "new@example.com",
        "password": "password123",
    })
    assert response.status_code == 200
    assert b"taken" in response.data.lower() or b"username" in response.data.lower()


def test_register_success_redirects(client):
    db.mongo.db.users.find_one.return_value = None
    db.mongo.db.users.insert_one.return_value = MagicMock(inserted_id=ObjectId())
    response = client.post("/register", data={
        "username": "newuser",
        "email": "new@example.com",
        "password": "securepassword",
    })
    assert response.status_code == 302


# ── POST /login ───────────────────────────────────────────────────────────────

def test_login_unknown_email(client):
    db.mongo.db.users.find_one.return_value = None
    response = client.post("/login", data={"email": "nobody@example.com", "password": "pw"})
    assert response.status_code == 200
    assert b"invalid" in response.data.lower()


def test_login_wrong_password(client):
    import bcrypt
    real_hash = bcrypt.hashpw(b"correctpassword", bcrypt.gensalt())
    db.mongo.db.users.find_one.return_value = _mock_user(password=real_hash)
    response = client.post("/login", data={"email": "alice@example.com", "password": "wrongpassword"})
    assert response.status_code == 200
    assert b"invalid" in response.data.lower()


def test_login_success_redirects(client):
    import bcrypt
    real_hash = bcrypt.hashpw(b"password123", bcrypt.gensalt())
    db.mongo.db.users.find_one.return_value = _mock_user(password=real_hash)
    response = client.post("/login", data={"email": "alice@example.com", "password": "password123"})
    assert response.status_code == 302


# ── GET /logout ───────────────────────────────────────────────────────────────

def test_logout_redirects(client):
    response = client.get("/logout")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_logout_clears_session(client, app):
    with client.session_transaction() as sess:
        sess["user_id"] = str(ObjectId())
        sess["username"] = "alice"
    client.get("/logout")
    with client.session_transaction() as sess:
        assert "user_id" not in sess
