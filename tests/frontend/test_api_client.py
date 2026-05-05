import pytest
from unittest.mock import MagicMock, patch

from services.api_client import (
    get_favorites,
    get_movie_details,
    get_movies_by_ids,
    get_similar_movies,
    recommend_from_favorites,
    recommend_movies,
    search_movies,
)


FAKE_MOVIE = {
    "id": "27205",
    "title": "Inception",
    "description": "A thief who steals corporate secrets...",
    "genre": "Action, Science Fiction",
    "year": 2010,
    "rating": 8.4,
    "poster_url": "https://example.com/poster.jpg",
    "director": "Christopher Nolan",
    "cast": ["Leonardo DiCaprio"],
}


def _mock_response(data, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = data
    resp.raise_for_status.return_value = None
    return resp


# ── search_movies ─────────────────────────────────────────────────────────────

@patch("services.api_client.requests.get")
def test_search_movies_calls_api(mock_get):
    mock_get.return_value = _mock_response([FAKE_MOVIE])
    results = search_movies("Inception")
    mock_get.assert_called_once()
    assert results[0]["title"] == "Inception"


# ── recommend_movies ──────────────────────────────────────────────────────────

@patch("services.api_client.requests.get")
def test_recommend_movies_adds_reason_field(mock_get):
    mock_get.return_value = _mock_response([FAKE_MOVIE])
    results = recommend_movies("sci-fi thriller")
    assert all("reason" in m for m in results)
    assert all("sci-fi thriller" in m["reason"] for m in results)


# ── recommend_from_favorites ──────────────────────────────────────────────────

@patch("services.api_client.requests.post")
def test_recommend_from_favorites_adds_reason(mock_post):
    mock_post.return_value = _mock_response([FAKE_MOVIE])
    titles = ["Inception", "Dune", "The Matrix", "Arrival"]
    results = recommend_from_favorites(titles)
    assert all("reason" in m for m in results)
    for title in titles:
        assert any(title in m["reason"] for m in results)


# ── get_movie_details ─────────────────────────────────────────────────────────

@patch("services.api_client.requests.get")
def test_get_movie_details_known_id(mock_get):
    mock_get.return_value = _mock_response(FAKE_MOVIE)
    movie = get_movie_details("27205")
    assert movie["id"] == "27205"
    assert "director" in movie
    assert "cast" in movie
    assert isinstance(movie["cast"], list)


@patch("services.api_client.requests.get")
def test_get_movie_details_unknown_id(mock_get):
    mock_get.return_value = _mock_response({"error": "Not found"}, status=404)
    mock_get.return_value.raise_for_status.side_effect = Exception("404")
    with pytest.raises(Exception):
        get_movie_details("9999")


# ── get_similar_movies ────────────────────────────────────────────────────────

@patch("services.api_client.requests.get")
def test_get_similar_movies_calls_api(mock_get):
    mock_get.return_value = _mock_response([FAKE_MOVIE])
    results = get_similar_movies("27205")
    assert len(results) > 0


# ── get_movies_by_ids ─────────────────────────────────────────────────────────

@patch("services.api_client.requests.post")
def test_get_movies_by_ids_preserves_order(mock_post):
    fake_movies = [
        {"id": "3", "title": "Three"},
        {"id": "1", "title": "One"},
        {"id": "2", "title": "Two"},
    ]
    mock_post.return_value = _mock_response(fake_movies)
    ids = ["3", "1", "2"]
    results = get_movies_by_ids(ids)
    assert [m["id"] for m in results] == ids


@patch("services.api_client.requests.post")
def test_get_movies_by_ids_empty_input(mock_post):
    mock_post.return_value = _mock_response([])
    assert get_movies_by_ids([]) == []
    mock_post.assert_not_called()


# ── get_favorites ─────────────────────────────────────────────────────────────

@patch("services.api_client.requests.post")
def test_get_favorites_for_logged_in_user(mock_post):
    from flask import session
    import db

    fake_watchlist = [{"movie_id": "27205"}, {"movie_id": "27206"}]
    db.mongo.db.watchlists.find.return_value = fake_watchlist

    mock_post.return_value = _mock_response([FAKE_MOVIE, FAKE_MOVIE])

    with patch("services.api_client.session", {"user_id": "507f1f77bcf86cd799439011"}):
        results = get_favorites()

    assert isinstance(results, list)
    assert len(results) == 2
    db.mongo.db.watchlists.find.assert_called_once()
