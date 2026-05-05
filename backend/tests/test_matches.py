"""
Tests for app/routers/matches.py.

Covers:
- GET /api/matches
    - Empty list when user has no matches
    - Returns matches sorted by created_at descending
    - is_new = True when current user is not in seen_by
    - is_new = False when current user is in seen_by
    - other_user is hydrated with the OTHER user's display info (incl. photo_url)
- PATCH /api/matches/{match_id}/seen
    - 404 when match_id is malformed
    - 404 when match exists but does not include the current user
    - $addToSet is used so the call is idempotent

The route is exercised by calling the handler directly with mocked
collections — same pattern as test_database.py.
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
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.routers.matches import get_matches, mark_seen


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _AsyncCursor:
    def __init__(self, items):
        self._items = list(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._items:
            raise StopAsyncIteration
        return self._items.pop(0)


def _matches_col_with(docs):
    col = MagicMock()
    col.find = MagicMock(return_value=_AsyncCursor(docs))
    col.find_one = AsyncMock(return_value=None)
    col.update_one = AsyncMock()
    return col


def _users_col_returning(other_doc):
    col = MagicMock()
    col.find_one = AsyncMock(return_value=other_doc)
    return col


# ===========================================================================
# GET /api/matches
# ===========================================================================

class TestGetMatchesEmpty:
    @pytest.mark.asyncio
    async def test_empty_when_user_has_no_matches(self):
        me = {"_id": ObjectId()}
        matches = _matches_col_with([])
        users = _users_col_returning(None)

        with (
            patch("app.routers.matches.get_matches_collection", return_value=matches),
            patch("app.routers.matches.get_users_collection", return_value=users),
        ):
            result = await get_matches(current_user=me)

        assert result == {"matches": []}


class TestGetMatchesSorting:
    @pytest.mark.asyncio
    async def test_sorted_by_created_at_desc(self):
        me_id = ObjectId()
        other_id = ObjectId()
        me = {"_id": me_id}
        now = datetime.now(timezone.utc)

        m_old = {
            "_id": ObjectId(),
            "user_ids": [str(me_id), str(other_id)],
            "seen_by": [],
            "created_at": now - timedelta(days=2),
        }
        m_new = {
            "_id": ObjectId(),
            "user_ids": [str(me_id), str(other_id)],
            "seen_by": [],
            "created_at": now,
        }
        matches = _matches_col_with([m_old, m_new])
        users = _users_col_returning({
            "_id": other_id,
            "display_name": "Pat",
            "age": 27,
            "city": "NYC",
            "spotify": {"top_genres": ["pop"]},
            "photo_url": None,
        })

        with (
            patch("app.routers.matches.get_matches_collection", return_value=matches),
            patch("app.routers.matches.get_users_collection", return_value=users),
        ):
            result = await get_matches(current_user=me)

        ids = [m["match_id"] for m in result["matches"]]
        assert ids == [str(m_new["_id"]), str(m_old["_id"])]


class TestIsNewFlag:
    @pytest.mark.asyncio
    async def test_is_new_true_when_user_not_in_seen_by(self):
        me_id = ObjectId()
        other_id = ObjectId()
        me = {"_id": me_id}
        match = {
            "_id": ObjectId(),
            "user_ids": [str(me_id), str(other_id)],
            "seen_by": [],
            "created_at": datetime.now(timezone.utc),
        }
        matches = _matches_col_with([match])
        users = _users_col_returning({
            "_id": other_id, "display_name": "Pat", "age": 27, "city": "NYC",
            "spotify": {"top_genres": []}, "photo_url": None,
        })

        with (
            patch("app.routers.matches.get_matches_collection", return_value=matches),
            patch("app.routers.matches.get_users_collection", return_value=users),
        ):
            result = await get_matches(current_user=me)

        assert result["matches"][0]["is_new"] is True

    @pytest.mark.asyncio
    async def test_is_new_false_when_user_already_in_seen_by(self):
        me_id = ObjectId()
        other_id = ObjectId()
        me = {"_id": me_id}
        match = {
            "_id": ObjectId(),
            "user_ids": [str(me_id), str(other_id)],
            "seen_by": [str(me_id)],
            "created_at": datetime.now(timezone.utc),
        }
        matches = _matches_col_with([match])
        users = _users_col_returning({
            "_id": other_id, "display_name": "Pat", "age": 27, "city": "NYC",
            "spotify": {"top_genres": []}, "photo_url": None,
        })

        with (
            patch("app.routers.matches.get_matches_collection", return_value=matches),
            patch("app.routers.matches.get_users_collection", return_value=users),
        ):
            result = await get_matches(current_user=me)

        assert result["matches"][0]["is_new"] is False


class TestOtherUserHydration:
    @pytest.mark.asyncio
    async def test_other_user_fields_populated(self):
        me_id = ObjectId()
        other_id = ObjectId()
        me = {"_id": me_id}
        match = {
            "_id": ObjectId(),
            "user_ids": [str(me_id), str(other_id)],
            "seen_by": [],
            "created_at": datetime.now(timezone.utc),
        }
        matches = _matches_col_with([match])
        users = _users_col_returning({
            "_id": other_id,
            "display_name": "Riley",
            "age": 30,
            "city": "Boston",
            "spotify": {"top_genres": ["indie", "rock"]},
            "photo_url": "https://example.com/photo.jpg",
        })

        with (
            patch("app.routers.matches.get_matches_collection", return_value=matches),
            patch("app.routers.matches.get_users_collection", return_value=users),
        ):
            result = await get_matches(current_user=me)

        other = result["matches"][0]["other_user"]
        assert other["user_id"] == str(other_id)
        assert other["display_name"] == "Riley"
        assert other["age"] == 30
        assert other["city"] == "Boston"
        assert other["top_genres"] == ["indie", "rock"]
        assert other["photo_url"] == "https://example.com/photo.jpg"

    @pytest.mark.asyncio
    async def test_other_user_falls_back_to_unknown_when_missing(self):
        me_id = ObjectId()
        other_id = ObjectId()
        me = {"_id": me_id}
        match = {
            "_id": ObjectId(),
            "user_ids": [str(me_id), str(other_id)],
            "seen_by": [],
            "created_at": datetime.now(timezone.utc),
        }
        matches = _matches_col_with([match])
        users = _users_col_returning(None)

        with (
            patch("app.routers.matches.get_matches_collection", return_value=matches),
            patch("app.routers.matches.get_users_collection", return_value=users),
        ):
            result = await get_matches(current_user=me)

        other = result["matches"][0]["other_user"]
        assert other["display_name"] == "Unknown"
        assert other["age"] == 0
        assert other["city"] == ""
        assert other["top_genres"] == []
        assert other["photo_url"] is None


# ===========================================================================
# PATCH /api/matches/{match_id}/seen
# ===========================================================================

class TestMarkSeen:
    @pytest.mark.asyncio
    async def test_404_when_match_id_is_malformed(self):
        me = {"_id": ObjectId()}
        matches = _matches_col_with([])

        with patch("app.routers.matches.get_matches_collection", return_value=matches):
            with pytest.raises(HTTPException) as exc:
                await mark_seen(match_id="not-an-objectid", current_user=me)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_404_when_match_does_not_include_current_user(self):
        me = {"_id": ObjectId()}
        matches = _matches_col_with([])
        matches.find_one = AsyncMock(return_value=None)

        with patch("app.routers.matches.get_matches_collection", return_value=matches):
            with pytest.raises(HTTPException) as exc:
                await mark_seen(match_id=str(ObjectId()), current_user=me)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_uses_add_to_set_for_idempotency(self):
        me_id = ObjectId()
        match_oid = ObjectId()
        me = {"_id": me_id}
        existing = {
            "_id": match_oid,
            "user_ids": [str(me_id), str(ObjectId())],
            "seen_by": [],
            "created_at": datetime.now(timezone.utc),
        }
        matches = _matches_col_with([])
        matches.find_one = AsyncMock(return_value=existing)

        with patch("app.routers.matches.get_matches_collection", return_value=matches):
            result = await mark_seen(match_id=str(match_oid), current_user=me)

        matches.update_one.assert_awaited_once()
        update_arg = matches.update_one.await_args[0][1]
        assert "$addToSet" in update_arg
        assert update_arg["$addToSet"] == {"seen_by": str(me_id)}
        assert result == {"detail": "Match marked as seen"}
