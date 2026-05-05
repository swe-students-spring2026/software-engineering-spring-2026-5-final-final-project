"""
Service layer that calls the recommendation-engine REST API for movie data
and MongoDB for user-specific data (watchlists).
"""

import os
from bson import ObjectId
from flask import session
import requests

REC_API_URL = os.getenv("REC_API_URL", "http://localhost:5001")


def _api_get(path: str, params: dict | None = None) -> dict | list:
    resp = requests.get(f"{REC_API_URL}{path}", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _api_post(path: str, payload: dict) -> dict | list:
    resp = requests.post(
        f"{REC_API_URL}{path}", json=payload, timeout=30
    )
    resp.raise_for_status()
    return resp.json()


def search_movies(query: str) -> list[dict]:
    """Standard keyword search that returns matching movies from the API."""
    return _api_get("/search", params={"q": query})


def recommend_movies(query: str) -> list[dict]:
    """Natural-language recommendation search (fallback to keyword search)."""
    results = search_movies(query)
    for movie in results:
        movie["reason"] = f'Matched your request: "{query}"'
    return results


def recommend_from_favorites(favorite_titles: list[str]) -> list[dict]:
    """Return personalized recommendations based on favorite movie titles."""
    results = _api_post(
        "/recommend",
        {"favorite_titles": favorite_titles, "k": 20},
    )
    favorites = ", ".join(title for title in favorite_titles if title)
    for movie in results:
        movie["reason"] = f"Cosine similarity match based on: {favorites}"
    return results


def get_movie_details(movie_id: str) -> dict:
    """Fetch full details for a single movie by ID."""
    movie = _api_get(f"/movies/{movie_id}")
    movie.setdefault("director", "Unknown")
    movie.setdefault("cast", [])
    return movie


def get_similar_movies(movie_id: str) -> list[dict]:
    """Fetch movies similar to a selected movie."""
    return _api_get(f"/movies/{movie_id}/similar")


def get_movies_by_ids(movie_ids: list[str]) -> list[dict]:
    """Fetch movies matching the provided IDs while preserving the ID order."""
    if not movie_ids:
        return []
    return _api_post("/movies/by-ids", {"movie_ids": movie_ids})


def get_favorites() -> list[dict]:
    """Fetch the current user's saved watchlist from MongoDB."""
    # Import here to avoid circular imports at module level; mongo is safe to use
    # inside request handlers because we are always called from within a route.
    from db import mongo

    user_id = session.get("user_id")
    if not user_id:
        return []

    docs = mongo.db.watchlists.find(
        {"user_id": ObjectId(user_id)}, {"movie_id": 1}
    )
    movie_ids = [doc["movie_id"] for doc in docs]
    return get_movies_by_ids(movie_ids)
