import pytest
from services.api_client import (
    PLACEHOLDER_MOVIES,
    get_favorites,
    get_movie_details,
    get_movies_by_ids,
    get_similar_movies,
    recommend_from_favorites,
    recommend_movies,
    search_movies,
)


# ── search_movies ─────────────────────────────────────────────────────────────

def test_search_by_title_match():
    results = search_movies("Lorem")
    assert any("Lorem" in m["title"] for m in results)


def test_search_by_genre_match():
    results = search_movies("drama")
    assert any(m["genre"].lower() == "drama" for m in results)


def test_search_case_insensitive():
    results = search_movies("LOREM")
    assert any("Lorem" in m["title"] for m in results)


def test_search_no_match_returns_all_movies():
    results = search_movies("xyznotamovie123")
    assert results == PLACEHOLDER_MOVIES


# ── recommend_movies ──────────────────────────────────────────────────────────

def test_recommend_movies_adds_reason_field():
    results = recommend_movies("sci-fi thriller")
    assert all("reason" in m for m in results)


def test_recommend_movies_reason_contains_query():
    results = recommend_movies("sci-fi thriller")
    assert all("sci-fi thriller" in m["reason"] for m in results)


def test_recommend_movies_returns_all_placeholder():
    results = recommend_movies("anything")
    assert len(results) == len(PLACEHOLDER_MOVIES)


# ── recommend_from_favorites ──────────────────────────────────────────────────

def test_recommend_from_favorites_adds_reason():
    results = recommend_from_favorites(["Inception", "Dune", "The Matrix", "Arrival"])
    assert all("reason" in m for m in results)


def test_recommend_from_favorites_includes_titles_in_reason():
    titles = ["Inception", "Dune", "The Matrix", "Arrival"]
    results = recommend_from_favorites(titles)
    for title in titles:
        assert any(title in m["reason"] for m in results)


# ── get_movie_details ─────────────────────────────────────────────────────────

def test_get_movie_details_known_id():
    movie = get_movie_details("1")
    assert movie["id"] == "1"
    assert "director" in movie
    assert "cast" in movie
    assert isinstance(movie["cast"], list)


def test_get_movie_details_unknown_id_returns_fallback():
    movie = get_movie_details("9999")
    assert "director" in movie
    assert "cast" in movie


# ── get_similar_movies ────────────────────────────────────────────────────────

def test_get_similar_movies_excludes_queried_movie():
    results = get_similar_movies("1")
    assert all(m["id"] != "1" for m in results)


def test_get_similar_movies_returns_multiple():
    results = get_similar_movies("1")
    assert len(results) > 0


# ── get_movies_by_ids ─────────────────────────────────────────────────────────

def test_get_movies_by_ids_preserves_order():
    ids = ["3", "1", "2"]
    results = get_movies_by_ids(ids)
    assert [m["id"] for m in results] == ids


def test_get_movies_by_ids_skips_unknown_ids():
    results = get_movies_by_ids(["1", "9999", "2"])
    assert len(results) == 2
    assert all(m["id"] in {"1", "2"} for m in results)


def test_get_movies_by_ids_empty_input():
    assert get_movies_by_ids([]) == []


# ── get_favorites ─────────────────────────────────────────────────────────────

def test_get_favorites_returns_list():
    results = get_favorites()
    assert isinstance(results, list)
    assert len(results) > 0
