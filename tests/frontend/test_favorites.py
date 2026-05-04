import pytest
from unittest.mock import MagicMock, patch
from bson import ObjectId

import db


FAKE_MOVIE = {"id": "42", "title": "Watchlisted Film", "genre": "Action", "year": 2022, "rating": 8.0}


# ── GET /watchlist ────────────────────────────────────────────────────────────

def test_watchlist_renders_for_anonymous(client):
    db.mongo.db.watchlists.find.return_value = iter([])
    with patch("routes.favorites.get_movies_by_ids", return_value=[]):
        response = client.get("/watchlist")
    assert response.status_code == 200


def test_watchlist_shows_saved_movies(client):
    user_id = ObjectId()
    with client.session_transaction() as sess:
        sess["user_id"] = str(user_id)
    db.mongo.db.watchlists.find.return_value = iter([{"movie_id": "42"}])
    with patch("routes.favorites.get_movies_by_ids", return_value=[FAKE_MOVIE]):
        response = client.get("/watchlist")
    assert response.status_code == 200
    assert b"Watchlisted Film" in response.data


def test_favorites_route_alias(client):
    db.mongo.db.watchlists.find.return_value = iter([])
    with patch("routes.favorites.get_movies_by_ids", return_value=[]):
        response = client.get("/favorites")
    assert response.status_code == 200


# ── POST /watchlist/toggle/<movie_id> ─────────────────────────────────────────

def test_toggle_unauthenticated_redirects_to_login(client):
    with client.session_transaction() as sess:
        sess.pop("user_id", None)
    response = client.post("/watchlist/toggle/42")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_toggle_adds_movie_when_not_present(client):
    user_id = ObjectId()
    with client.session_transaction() as sess:
        sess["user_id"] = str(user_id)
    db.mongo.db.watchlists.find_one.return_value = None
    db.mongo.db.watchlists.insert_one.return_value = MagicMock()
    response = client.post("/watchlist/toggle/42", data={"next": "/watchlist"})
    db.mongo.db.watchlists.insert_one.assert_called_once()
    assert response.status_code == 302


def test_toggle_removes_movie_when_already_present(client):
    user_id = ObjectId()
    existing_id = ObjectId()
    with client.session_transaction() as sess:
        sess["user_id"] = str(user_id)
    db.mongo.db.watchlists.find_one.return_value = {"_id": existing_id, "movie_id": "42"}
    db.mongo.db.watchlists.delete_one.return_value = MagicMock()
    response = client.post("/watchlist/toggle/42", data={"next": "/watchlist"})
    db.mongo.db.watchlists.delete_one.assert_called_once_with({"_id": existing_id})
    assert response.status_code == 302


def test_toggle_redirects_to_next_param(client):
    user_id = ObjectId()
    with client.session_transaction() as sess:
        sess["user_id"] = str(user_id)
    db.mongo.db.watchlists.find_one.return_value = None
    db.mongo.db.watchlists.insert_one.return_value = MagicMock()
    response = client.post("/watchlist/toggle/42", data={"next": "/movie/42"})
    assert "/movie/42" in response.headers["Location"]


def test_toggle_falls_back_to_watchlist_without_next(client):
    user_id = ObjectId()
    with client.session_transaction() as sess:
        sess["user_id"] = str(user_id)
    db.mongo.db.watchlists.find_one.return_value = None
    db.mongo.db.watchlists.insert_one.return_value = MagicMock()
    response = client.post("/watchlist/toggle/42")
    assert "/watchlist" in response.headers["Location"] or "/favorites" in response.headers["Location"]
