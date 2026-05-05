"""
HTTP client for the recommendation-engine service.

All movie data — search, recommendations, details, similar — is served by the
recommendation-engine subsystem over HTTP. This module is the only place in
the frontend that knows about that service; routes call these functions and
get back plain dicts/lists, the same shape the templates already expect.

User-specific data (favorites/watchlist) lives in MongoDB and is read here
via the shared `mongo` instance, not through the rec-engine.

Configuration:
    RECOMMENDATION_API_URL   base URL of the rec-engine service
                             (default: http://recommendation-engine:8000)
"""

import logging
import os
from typing import Any
import requests
from bson import ObjectId
from flask import session
from db import mongo

log = logging.getLogger(__name__)

API_BASE_URL = os.getenv("RECOMMENDATION_API_URL",
                         "http://recommendation-engine:8000")
DEFAULT_TIMEOUT = float(os.getenv("RECOMMENDATION_API_TIMEOUT", "5"))


# ── low-level HTTP helpers ───────────────────────────────────────────────────
def _get(path: str, params: dict | None = None) -> Any:
    return _request("GET", path, params=params)

def _post(path: str, json: dict | None = None) -> Any:
    return _request("POST", path, json=json)

def _request(method: str, path: str, **kwargs) -> Any:
    url = f"{API_BASE_URL.rstrip('/')}{path}"
    try:
        response = requests.request(
            method, url, timeout=DEFAULT_TIMEOUT, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        log.warning("recommendation-engine %s %s failed: %s",
                    method, path, exc)
        return None

# ── public API used by routes ────────────────────────────────────────────────
def search_movies(query: str) -> list[dict]:
    """Direct keyword search by title/genre."""
    data = _get("/search", params={"q": query, "mode": "direct"})
    return data.get("results", []) if data else []

def recommend_movies(query: str) -> list[dict]:
    """Natural-language semantic recommendation search."""
    data = _get("/search", params={"q": query, "mode": "intent"})
    return data.get("results", []) if data else []

def recommend_from_favorites(favorite_titles: list[str]) -> list[dict]:
    """Personalized recommendations from four favorite movie titles."""
    titles = [t for t in favorite_titles if t]
    if not titles:
        return []
    data = _post("/recommend", json={"favorite_titles": titles})
    return data.get("results", []) if data else []

def get_movie_details(movie_id: str) -> dict:
    """Full details for a single movie."""
    data = _get(f"/movies/{movie_id}")
    return data or {}

def get_similar_movies(movie_id: str) -> list[dict]:
    """Movies similar to the given movie."""
    data = _get(f"/movies/{movie_id}/similar")
    return data.get("results", []) if data else []

def get_movies_by_ids(movie_ids: list[str]) -> list[dict]:
    """Hydrate a list of movie IDs (e.g. from a watchlist) into full movie dicts.

    Preserves the order of `movie_ids` and silently drops any IDs the
    rec-engine doesn't recognise.
    """
    if not movie_ids:
        return []
    data = _post("/movies/batch", json={"ids": movie_ids})
    if not data:
        return []
    movies_by_id = {m["id"]: m for m in data.get("results", [])}
    return [movies_by_id[mid] for mid in movie_ids if mid in movies_by_id]


def get_favorites() -> list[dict]:
    """The current user's saved favorites (a.k.a. watchlist), hydrated."""
    user_id = _current_user_id()
    if user_id is None:
        return []

    docs = mongo.db.watchlists.find(
        {"user_id": user_id},
        {"movie_id": 1},
        sort=[("added_at", -1)],
    )
    movie_ids = [doc["movie_id"] for doc in docs]
    return get_movies_by_ids(movie_ids)

# ── internal ─────────────────────────────────────────────────────────────────
def _current_user_id() -> ObjectId | None:
    uid = session.get("user_id")
    return ObjectId(uid) if uid else None
