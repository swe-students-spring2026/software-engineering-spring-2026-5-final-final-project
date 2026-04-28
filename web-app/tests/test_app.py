"""Minimal web-app tests
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


def _import_web_app_module():
    os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
    os.environ.setdefault("MONGO_DBNAME", "potatoes_test")
    os.environ.setdefault("SECRET_KEY", "test")

    try:
        import app as web_app_module  # type: ignore
    except ModuleNotFoundError:
        web_app_dir = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(web_app_dir))
        import app as web_app_module  # type: ignore

    return web_app_module


@pytest.fixture()
def web_app_module():
    return _import_web_app_module()


@pytest.fixture()
def flask_app(web_app_module):
    return web_app_module.app


def test_login_page_renders(flask_app):
    client = flask_app.test_client()
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"<h1>Login</h1>" in resp.data


def test_signup_page_renders(flask_app):
    client = flask_app.test_client()
    resp = client.get("/signup")
    assert resp.status_code == 200
    assert b"Sign Up" in resp.data or b"Create Account" in resp.data


def test_protected_home_redirects_to_login(flask_app):
    client = flask_app.test_client()
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (301, 302)
    assert "/login" in (resp.headers.get("Location") or "")


def test_login_success_redirects_to_home(monkeypatch, flask_app, web_app_module):
    class FakeUsers:
        def find_one(self, query):
            if query == {"email": "test@example.com"}:
                return {"_id": "u1", "email": "test@example.com", "password": "pw"}
            return None

    monkeypatch.setattr(web_app_module, "db", SimpleNamespace(users=FakeUsers()))

    client = flask_app.test_client()
    resp = client.post(
        "/login",
        data={"email": "test@example.com", "password": "pw"},
        follow_redirects=False,
    )
    assert resp.status_code in (301, 302)
    assert resp.headers.get("Location", "").endswith("/")


def test_login_invalid_credentials_shows_error(monkeypatch, flask_app, web_app_module):
    class FakeUsers:
        def find_one(self, _query):
            return None

    monkeypatch.setattr(web_app_module, "db", SimpleNamespace(users=FakeUsers()))

    client = flask_app.test_client()
    resp = client.post("/login", data={"email": "nope@example.com", "password": "bad"})
    assert resp.status_code == 200
    assert b"Invalid email or password" in resp.data
