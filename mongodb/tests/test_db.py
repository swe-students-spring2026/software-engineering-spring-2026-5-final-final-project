"""
Unit tests for mongodb/db.py and mongodb/api.py
Uses mongomock to avoid needing a real MongoDB connection.
Run with: pytest tests/test_db.py --cov=db --cov=api --cov-report=term-missing
"""

import os
import pytest
import mongomock
from unittest.mock import patch, MagicMock

os.environ.setdefault("MONGO_URI", "mongodb://fake-atlas-host/rove_beetle")

import db
from api import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture(autouse=True)
def patch_mongo():
    """Use a single shared mongomock client for all db operations per test."""
    mock_client = mongomock.MongoClient()
    db._client = mock_client
    yield
    db._client = None


# --- make_cache_key ---

def test_make_cache_key_is_deterministic():
    key1 = db.make_cache_key("noisy streets", "")
    key2 = db.make_cache_key("noisy streets", "")
    assert key1 == key2


def test_make_cache_key_different_queries_differ():
    key1 = db.make_cache_key("noisy streets", "")
    key2 = db.make_cache_key("quiet park", "")
    assert key1 != key2


def test_make_cache_key_strips_and_lowercases():
    key1 = db.make_cache_key("  Noisy Streets  ", "")
    key2 = db.make_cache_key("noisy streets", "")
    assert key1 == key2


# --- db save and get ---

def test_save_and_get_cached_result():
    data = {"place_type": "library", "reversed_attribute": "loud", "results": []}
    db.save_cached_result("quiet study spot", "", data)
    result = db.get_cached_result("quiet study spot", "")
    assert result is not None
    assert result["place_type"] == "library"


def test_get_cached_result_returns_none_if_not_found():
    result = db.get_cached_result("this query was never saved", "")
    assert result is None


def test_save_overwrites_existing_cache():
    data1 = {"place_type": "park", "reversed_attribute": "noisy", "results": []}
    data2 = {"place_type": "library", "reversed_attribute": "loud", "results": [1, 2]}
    db.save_cached_result("my query", "", data1)
    db.save_cached_result("my query", "", data2)
    result = db.get_cached_result("my query", "")
    assert result["place_type"] == "library"
    assert len(result["results"]) == 2


# --- clear_cache ---

def test_clear_cache_removes_all_entries():
    data = {"place_type": "cafe", "reversed_attribute": "unsafe", "results": []}
    db.save_cached_result("cozy cafe", "", data)
    db.clear_cache()
    result = db.get_cached_result("cozy cafe", "")
    assert result is None


# --- health_check ---

def test_health_check_returns_true_when_connected():
    with patch("db.MongoClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_instance.admin.command.return_value = {"ok": 1}
        assert db.health_check() is True


def test_health_check_returns_false_when_unreachable():
    with patch("db.MongoClient") as mock_client:
        mock_client.side_effect = Exception("Connection refused")
        assert db.health_check() is False


# --- missing MONGO_URI ---

def test_missing_mongo_uri_raises(monkeypatch):
    monkeypatch.delenv("MONGO_URI", raising=False)
    db._client = None
    with pytest.raises(RuntimeError, match="MONGO_URI"):
        db.get_client()


# --- API: GET /health ---

def test_api_health_ok():
    with patch("api.health_check", return_value=True):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["mongo"] == "ok"


def test_api_health_unavailable():
    with patch("api.health_check", return_value=False):
        response = client.get("/health")
        assert response.status_code == 503


# --- API: POST /cache and GET /cache ---

def test_api_save_and_get_cache():
    data = {"place_type": "gym", "reversed_attribute": "dirty", "results": []}
    post_response = client.post("/cache", json={"query": "safe gym", "data": data})
    assert post_response.status_code == 200
    assert post_response.json()["status"] == "saved"

    get_response = client.get("/cache", params={"query": "safe gym"})
    assert get_response.status_code == 200
    assert get_response.json()["data"]["place_type"] == "gym"


def test_api_get_cache_not_found():
    response = client.get("/cache", params={"query": "nonexistent query xyz"})
    assert response.status_code == 404


# --- API: DELETE /cache ---

def test_api_delete_cache():
    data = {"place_type": "park", "reversed_attribute": "noisy", "results": []}
    client.post("/cache", json={"query": "quiet park", "data": data})
    delete_response = client.delete("/cache")
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "cleared"
    get_response = client.get("/cache", params={"query": "quiet park"})
    assert get_response.status_code == 404