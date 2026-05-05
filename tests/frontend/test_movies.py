import pytest
from unittest.mock import patch, MagicMock
from bson import ObjectId

import db
from routes.movies import _safe_back_url


FAKE_MOVIE = {
    "id": "1",
    "title": "Test Movie",
    "description": "A test.",
    "genre": "Drama",
    "year": 2020,
    "rating": 7.5,
    "director": "Jane Doe",
    "cast": ["Actor A"],
    "similarity": 0.9,
}


# ── _safe_back_url ─────────────────────────────────────────────────────────────

def test_safe_back_url_valid_relative_param(app):
    with app.test_request_context("/movie/1"):
        assert _safe_back_url("/search?q=test", None) == "/search?q=test"


def test_safe_back_url_rejects_protocol_relative(app):
    with app.test_request_context("/movie/1"):
        assert _safe_back_url("//evil.com", None) is None


def test_safe_back_url_uses_referrer_when_no_param(app):
    with app.test_request_context("/movie/1"):
        result = _safe_back_url(None, "http://localhost/search?q=action")
    assert result == "/search?q=action"


def test_safe_back_url_referrer_same_as_current_is_none(app):
    with app.test_request_context("/movie/1"):
        result = _safe_back_url(None, "http://localhost/movie/1")
    assert result is None


def test_safe_back_url_none_when_no_param_or_referrer(app):
    with app.test_request_context("/movie/1"):
        assert _safe_back_url(None, None) is None


# ── GET / (home) ──────────────────────────────────────────────────────────────

def test_home_renders(client):
    with patch("routes.movies.get_favorites", return_value=[]), \
         patch("routes.movies.recommend_from_favorites", return_value=[]):
        db.mongo.db.watchlists.find.return_value = iter([])
        response = client.get("/")
    assert response.status_code == 200


def test_home_with_no_favorites_skips_recommendations(client):
    with patch("routes.movies.get_favorites", return_value=[]) as gf, \
         patch("routes.movies.recommend_from_favorites") as rm:
        db.mongo.db.watchlists.find.return_value = iter([])
        client.get("/")
    rm.assert_not_called()


# ── GET /search ───────────────────────────────────────────────────────────────

def test_search_empty_query_renders_empty(client):
    db.mongo.db.watchlists.find.return_value = iter([])
    response = client.get("/search?q=")
    assert response.status_code == 200


def test_search_direct_mode(client):
    db.mongo.db.watchlists.find.return_value = iter([])
    db.mongo.db.history.insert_one.return_value = MagicMock()
    with patch("routes.movies.handle_search", return_value={
        "mode": "direct", "query": "Jaws", "results": [FAKE_MOVIE],
    }):
        response = client.get("/search?q=Jaws")
    assert response.status_code == 200
    assert b"Jaws" in response.data


def test_search_saves_history_for_logged_in_user(client, app):
    user_id = str(ObjectId())
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
    db.mongo.db.watchlists.find.return_value = iter([])
    db.mongo.db.history.insert_one.return_value = MagicMock()
    with patch("routes.movies.handle_search", return_value={
        "mode": "direct", "query": "Jaws", "results": [],
    }):
        client.get("/search?q=Jaws")
    db.mongo.db.history.insert_one.assert_called_once()


def test_search_skips_history_for_anonymous_user(client):
    with client.session_transaction() as sess:
        sess.pop("user_id", None)
    db.mongo.db.watchlists.find.return_value = iter([])
    with patch("routes.movies.handle_search", return_value={
        "mode": "direct", "query": "Jaws", "results": [],
    }):
        client.get("/search?q=Jaws")
    db.mongo.db.history.insert_one.assert_not_called()


# ── POST /recommendations ─────────────────────────────────────────────────────

def test_recommendations_missing_titles_shows_error(client):
    response = client.post("/recommendations", data={
        "favorite_1": "Inception",
        "favorite_2": "",
        "favorite_3": "Dune",
        "favorite_4": "",
    })
    assert response.status_code == 200
    assert b"four" in response.data.lower() or b"enter" in response.data.lower()


def test_recommendations_success(client):
    db.mongo.db.watchlists.find.return_value = iter([])
    db.mongo.db.history.insert_one.return_value = MagicMock()
    with patch("routes.movies.recommend_from_favorites", return_value=[FAKE_MOVIE]):
        response = client.post("/recommendations", data={
            "favorite_1": "Inception",
            "favorite_2": "The Matrix",
            "favorite_3": "Interstellar",
            "favorite_4": "Dune",
        })
    assert response.status_code == 200


# ── GET /movie/<id> ───────────────────────────────────────────────────────────

def test_movie_detail_renders(client):
    db.mongo.db.watchlists.find.return_value = iter([])
    with patch("routes.movies.get_movie_details", return_value=FAKE_MOVIE), \
         patch("routes.movies.get_similar_movies", return_value=[]):
        response = client.get("/movie/1")
    assert response.status_code == 200
    assert b"Test Movie" in response.data
