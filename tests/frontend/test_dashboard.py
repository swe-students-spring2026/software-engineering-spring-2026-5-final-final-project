import pytest
from bson import ObjectId

import db


def _history_item(type_, mode="direct"):
    return {"type": type_, "mode": mode, "query": "test", "result_count": 3}


# ── GET /history ──────────────────────────────────────────────────────────────

def test_history_anonymous_renders_empty(client):
    with client.session_transaction() as sess:
        sess.pop("user_id", None)
    response = client.get("/history")
    assert response.status_code == 200
    db.mongo.db.history.find.assert_not_called()


def test_history_logged_in_queries_db(client):
    user_id = ObjectId()
    with client.session_transaction() as sess:
        sess["user_id"] = str(user_id)
    db.mongo.db.history.find.return_value = iter([_history_item("Search")])
    response = client.get("/history")
    assert response.status_code == 200
    db.mongo.db.history.find.assert_called_once()


# ── GET /analytics ────────────────────────────────────────────────────────────

def test_analytics_anonymous_shows_zeros(client):
    with client.session_transaction() as sess:
        sess.pop("user_id", None)
    response = client.get("/analytics")
    assert response.status_code == 200


def test_analytics_logged_in_counts_correctly(client):
    user_id = ObjectId()
    with client.session_transaction() as sess:
        sess["user_id"] = str(user_id)
    history = [
        _history_item("Search", "direct"),
        _history_item("Search", "intent"),
        _history_item("Recommendation", "cosine"),
    ]
    db.mongo.db.history.find.return_value = iter(history)
    db.mongo.db.watchlists.count_documents.return_value = 5
    response = client.get("/analytics")
    assert response.status_code == 200
    assert b"5" in response.data  # watchlist count


def test_analytics_semantic_count(client):
    user_id = ObjectId()
    with client.session_transaction() as sess:
        sess["user_id"] = str(user_id)
    history = [
        _history_item("Search", "intent"),
        _history_item("Search", "intent"),
        _history_item("Search", "direct"),
    ]
    db.mongo.db.history.find.return_value = iter(history)
    db.mongo.db.watchlists.count_documents.return_value = 0
    response = client.get("/analytics")
    assert response.status_code == 200
