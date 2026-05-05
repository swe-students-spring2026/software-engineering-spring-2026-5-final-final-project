"""Tests for the X-API-Key middleware in api/app.py.

Covers the non-TESTING enforcement path (the existing tests all run with
TESTING=True so they skip the middleware entirely).
"""

import importlib


class FakeUsersCollection:
    def find_one(self, query):
        return None


def load_api_module(monkeypatch, secret=None):
    monkeypatch.setenv("MONGO_URI", "mongodb://example:27017/")
    monkeypatch.setenv("MONGO_DBNAME", "splitring_test")
    if secret is None:
        monkeypatch.delenv("API_SHARED_SECRET", raising=False)
    else:
        monkeypatch.setenv("API_SHARED_SECRET", secret)
    module = importlib.import_module("api.app")
    return importlib.reload(module)


def test_api_key_required_when_secret_set(monkeypatch):
    api_module = load_api_module(monkeypatch, secret="topsecret")
    api_module.db = {"users": FakeUsersCollection()}
    # Important: TESTING is NOT set here, so the middleware enforces.
    client = api_module.app.test_client()

    response = client.post("/api/login", json={"username": "x", "password": "y"})
    assert response.status_code == 401
    assert response.get_json()["error"] == "unauthorized"


def test_api_key_accepted_when_correct(monkeypatch):
    api_module = load_api_module(monkeypatch, secret="topsecret")
    api_module.db = {"users": FakeUsersCollection()}
    client = api_module.app.test_client()

    response = client.post(
        "/api/login",
        json={"username": "x", "password": "y"},
        headers={"X-API-Key": "topsecret"},
    )
    # Wrong creds (user doesn't exist) -> 401, but NOT the auth-middleware 401.
    # Either way, the middleware let the request through.
    assert response.status_code in (401, 400)
    body = response.get_json()
    assert body["error"] != "unauthorized"


def test_api_key_unset_allows_request_in_dev(monkeypatch):
    api_module = load_api_module(monkeypatch, secret=None)
    api_module.db = {"users": FakeUsersCollection()}
    client = api_module.app.test_client()

    response = client.post("/api/login", json={"username": "x", "password": "y"})
    # Middleware passes through; login itself returns 401 for missing user.
    body = response.get_json()
    assert body["error"] != "unauthorized"
