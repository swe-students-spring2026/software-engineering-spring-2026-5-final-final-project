"""
Tests for app/routers/feed.py.

Covers GET /api/feed:
- 403 when current user has not connected Spotify
- Excludes self and already-liked users from the candidate pool
- Applies gender_preference, age_range_preference, and city filters
- Sorts candidates by match_score descending
- Pagination: page 0, page 1, has_more boundary

The route is exercised by calling the handler directly with mocked
collections — the same pattern used in test_database.py.
"""

# ---------------------------------------------------------------------------
# Env-var bootstrap — must precede any app.* import
# ---------------------------------------------------------------------------
import os

os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017/vibe_test")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("SPOTIFY_CLIENT_ID", "fake")
os.environ.setdefault("SPOTIFY_CLIENT_SECRET", "fake")
os.environ.setdefault("SPOTIFY_REDIRECT_URI", "http://localhost:8000/api/spotify/callback")

from app.config import get_settings
get_settings.cache_clear()

# ---------------------------------------------------------------------------
# Standard imports
# ---------------------------------------------------------------------------
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.routers.feed import get_feed


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_doc(
    _id=None,
    display_name="Me",
    age=25,
    city="NYC",
    is_spotify_connected=True,
    gender=None,
    gender_preference=None,
    age_range_preference=None,
    top_genres=None,
    top_artists=None,
    audio_features=None,
):
    return {
        "_id": _id or ObjectId(),
        "display_name": display_name,
        "age": age,
        "city": city,
        "bio": None,
        "gender": gender,
        "gender_preference": gender_preference,
        "age_range_preference": age_range_preference,
        "is_spotify_connected": is_spotify_connected,
        "spotify": {
            "top_genres": top_genres or [],
            "top_artists": [{"id": a, "name": a} for a in (top_artists or [])],
            "audio_features": audio_features,
        },
    }


class _AsyncCursor:
    """Minimal async iterator standing in for motor's find() cursor."""

    def __init__(self, items):
        self._items = list(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._items:
            raise StopAsyncIteration
        return self._items.pop(0)


def _likes_collection_with(liked_to_ids):
    likes_col = MagicMock()
    likes_col.find = MagicMock(
        return_value=_AsyncCursor([{"to_user_id": uid} for uid in liked_to_ids])
    )
    return likes_col


def _users_collection_with(candidates):
    users_col = MagicMock()
    users_col.find = MagicMock(return_value=_AsyncCursor(candidates))
    return users_col


# ===========================================================================
# Spotify gating
# ===========================================================================

class TestSpotifyGate:
    @pytest.mark.asyncio
    async def test_raises_403_when_not_connected(self):
        me = _user_doc(is_spotify_connected=False)
        with pytest.raises(HTTPException) as exc:
            await get_feed(page=0, current_user=me)
        assert exc.value.status_code == 403
        assert exc.value.detail == "spotify_required"


# ===========================================================================
# Candidate exclusion
# ===========================================================================

class TestCandidateExclusion:
    @pytest.mark.asyncio
    async def test_excludes_self_and_already_liked(self):
        me = _user_doc()
        liked_id = str(ObjectId())
        likes_col = _likes_collection_with([liked_id])
        users_col = _users_collection_with([])

        with (
            patch("app.routers.feed.get_likes_collection", return_value=likes_col),
            patch("app.routers.feed.get_users_collection", return_value=users_col),
        ):
            await get_feed(page=0, current_user=me)

        query = users_col.find.call_args[0][0]
        excluded = query["_id"]["$nin"]
        assert me["_id"] in excluded
        assert ObjectId(liked_id) in excluded


# ===========================================================================
# Filters
# ===========================================================================

class TestFilters:
    @pytest.mark.asyncio
    async def test_gender_preference_applied_when_specific(self):
        me = _user_doc(gender_preference="female")
        likes_col = _likes_collection_with([])
        users_col = _users_collection_with([])

        with (
            patch("app.routers.feed.get_likes_collection", return_value=likes_col),
            patch("app.routers.feed.get_users_collection", return_value=users_col),
        ):
            await get_feed(page=0, current_user=me)

        query = users_col.find.call_args[0][0]
        assert query["gender"] == "female"

    @pytest.mark.asyncio
    async def test_gender_preference_skipped_when_any(self):
        me = _user_doc(gender_preference="any")
        likes_col = _likes_collection_with([])
        users_col = _users_collection_with([])

        with (
            patch("app.routers.feed.get_likes_collection", return_value=likes_col),
            patch("app.routers.feed.get_users_collection", return_value=users_col),
        ):
            await get_feed(page=0, current_user=me)

        query = users_col.find.call_args[0][0]
        assert "gender" not in query

    @pytest.mark.asyncio
    async def test_age_range_preference_applied(self):
        me = _user_doc(age_range_preference={"min": 22, "max": 30})
        likes_col = _likes_collection_with([])
        users_col = _users_collection_with([])

        with (
            patch("app.routers.feed.get_likes_collection", return_value=likes_col),
            patch("app.routers.feed.get_users_collection", return_value=users_col),
        ):
            await get_feed(page=0, current_user=me)

        query = users_col.find.call_args[0][0]
        assert query["age"] == {"$gte": 22, "$lte": 30}

    @pytest.mark.asyncio
    async def test_city_filter_applied(self):
        me = _user_doc(city="Brooklyn")
        likes_col = _likes_collection_with([])
        users_col = _users_collection_with([])

        with (
            patch("app.routers.feed.get_likes_collection", return_value=likes_col),
            patch("app.routers.feed.get_users_collection", return_value=users_col),
        ):
            await get_feed(page=0, current_user=me)

        query = users_col.find.call_args[0][0]
        assert query["city"] == "Brooklyn"


# ===========================================================================
# Ranking and pagination
# ===========================================================================

class TestRankingAndPagination:
    @pytest.mark.asyncio
    async def test_results_sorted_by_match_score_desc(self):
        me = _user_doc(top_genres=["pop", "rock"])
        a = _user_doc(top_genres=["jazz"])           # lower score
        b = _user_doc(top_genres=["pop", "rock"])    # perfect genre overlap
        c = _user_doc(top_genres=["pop"])            # partial overlap

        likes_col = _likes_collection_with([])
        users_col = _users_collection_with([a, b, c])

        with (
            patch("app.routers.feed.get_likes_collection", return_value=likes_col),
            patch("app.routers.feed.get_users_collection", return_value=users_col),
        ):
            result = await get_feed(page=0, current_user=me)

        scores = [p["match_score"] for p in result["profiles"]]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_page_zero_returns_first_ten(self):
        me = _user_doc()
        candidates = [_user_doc(display_name=f"u{i}") for i in range(15)]
        likes_col = _likes_collection_with([])
        users_col = _users_collection_with(candidates)

        with (
            patch("app.routers.feed.get_likes_collection", return_value=likes_col),
            patch("app.routers.feed.get_users_collection", return_value=users_col),
        ):
            result = await get_feed(page=0, current_user=me)

        assert len(result["profiles"]) == 10
        assert result["page"] == 0
        assert result["has_more"] is True

    @pytest.mark.asyncio
    async def test_page_one_returns_remainder_and_has_more_false(self):
        me = _user_doc()
        candidates = [_user_doc(display_name=f"u{i}") for i in range(15)]
        likes_col = _likes_collection_with([])
        users_col = _users_collection_with(candidates)

        with (
            patch("app.routers.feed.get_likes_collection", return_value=likes_col),
            patch("app.routers.feed.get_users_collection", return_value=users_col),
        ):
            result = await get_feed(page=1, current_user=me)

        assert len(result["profiles"]) == 5
        assert result["page"] == 1
        assert result["has_more"] is False

    @pytest.mark.asyncio
    async def test_empty_candidate_pool(self):
        me = _user_doc()
        likes_col = _likes_collection_with([])
        users_col = _users_collection_with([])

        with (
            patch("app.routers.feed.get_likes_collection", return_value=likes_col),
            patch("app.routers.feed.get_users_collection", return_value=users_col),
        ):
            result = await get_feed(page=0, current_user=me)

        assert result["profiles"] == []
        assert result["has_more"] is False


# ===========================================================================
# Profile shape
# ===========================================================================

class TestProfileShape:
    @pytest.mark.asyncio
    async def test_photo_url_is_always_none_in_feed(self):
        me = _user_doc()
        candidates = [_user_doc()]
        likes_col = _likes_collection_with([])
        users_col = _users_collection_with(candidates)

        with (
            patch("app.routers.feed.get_likes_collection", return_value=likes_col),
            patch("app.routers.feed.get_users_collection", return_value=users_col),
        ):
            result = await get_feed(page=0, current_user=me)

        assert all(p["photo_url"] is None for p in result["profiles"])
