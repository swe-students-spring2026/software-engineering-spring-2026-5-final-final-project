"""
Tests for app/routers/likes.py.

Covers POST /api/likes/{user_id} and DELETE /api/likes/{user_id}:
- 400 when liking yourself
- 404 when target user does not exist (bad ObjectId or no doc)
- 429 when daily like limit reached
- Daily reset rolls likes_sent_today back to 0
- Idempotent re-like returns matched=False without duplicate insert
- Mutual like creates a matches document and returns matched=True
- Mutual like is idempotent if a match already exists
- DELETE removes the like document

The route is exercised by calling the handler directly with mocked
collections — same pattern as test_database.py / test_feed.py.
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

from app.routers.likes import like_user, unlike_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _me(_id=None, likes_sent_today=0, likes_reset_at=None):
    return {
        "_id": _id or ObjectId(),
        "likes_sent_today": likes_sent_today,
        "likes_reset_at": likes_reset_at,
    }


def _users_col(target_doc=None, raise_on_find=False):
    col = MagicMock()
    if raise_on_find:
        col.find_one = AsyncMock(side_effect=Exception("bad id"))
    else:
        col.find_one = AsyncMock(return_value=target_doc)
    col.update_one = AsyncMock()
    return col


def _likes_col(existing_self_like=None, reverse_like=None):
    col = MagicMock()

    async def find_one_side_effect(query, *args, **kwargs):
        if query.get("from_user_id") and query.get("to_user_id"):
            # Distinguish self-like vs reverse-like by which direction we asked for.
            # The route checks the self-like first, then the reverse.
            return find_one_side_effect.queue.pop(0) if find_one_side_effect.queue else None
        return None

    find_one_side_effect.queue = [existing_self_like, reverse_like]
    col.find_one = AsyncMock(side_effect=find_one_side_effect)
    col.insert_one = AsyncMock()
    col.delete_one = AsyncMock()
    return col


def _matches_col(existing_match=None, inserted_id=None):
    col = MagicMock()
    col.find_one = AsyncMock(return_value=existing_match)
    insert_result = MagicMock()
    insert_result.inserted_id = inserted_id or ObjectId()
    col.insert_one = AsyncMock(return_value=insert_result)
    return col


# ===========================================================================
# Validation
# ===========================================================================

class TestLikeValidation:
    @pytest.mark.asyncio
    async def test_cannot_like_yourself(self):
        me = _me()
        with pytest.raises(HTTPException) as exc:
            await like_user(user_id=str(me["_id"]), current_user=me)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_404_when_objectid_is_malformed(self):
        me = _me()
        users = _users_col(raise_on_find=True)
        with patch("app.routers.likes.get_users_collection", return_value=users):
            with pytest.raises(HTTPException) as exc:
                await like_user(user_id="not-an-objectid", current_user=me)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_404_when_target_does_not_exist(self):
        me = _me()
        users = _users_col(target_doc=None)
        with patch("app.routers.likes.get_users_collection", return_value=users):
            with pytest.raises(HTTPException) as exc:
                await like_user(user_id=str(ObjectId()), current_user=me)
        assert exc.value.status_code == 404


# ===========================================================================
# Rate limiting
# ===========================================================================

class TestRateLimit:
    @pytest.mark.asyncio
    async def test_429_when_at_daily_limit(self):
        me = _me(likes_sent_today=50)
        target_id = str(ObjectId())
        users = _users_col(target_doc={"_id": ObjectId(target_id)})

        with (
            patch("app.routers.likes.get_users_collection", return_value=users),
            patch("app.routers.likes.get_likes_collection", return_value=_likes_col()),
        ):
            with pytest.raises(HTTPException) as exc:
                await like_user(user_id=target_id, current_user=me)
        assert exc.value.status_code == 429

    @pytest.mark.asyncio
    async def test_daily_reset_rolls_counter_to_zero(self):
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        me = _me(likes_sent_today=50, likes_reset_at=yesterday)
        target_id = str(ObjectId())
        users = _users_col(target_doc={"_id": ObjectId(target_id)})
        likes = _likes_col()

        with (
            patch("app.routers.likes.get_users_collection", return_value=users),
            patch("app.routers.likes.get_likes_collection", return_value=likes),
            patch("app.routers.likes.get_matches_collection", return_value=_matches_col()),
        ):
            result = await like_user(user_id=target_id, current_user=me)

        # Reset path triggers a $set on likes_sent_today=0
        reset_call = next(
            c for c in users.update_one.await_args_list
            if "$set" in c.args[1] and c.args[1]["$set"].get("likes_sent_today") == 0
        )
        assert reset_call is not None
        assert result["matched"] is False


# ===========================================================================
# Like creation and idempotency
# ===========================================================================

class TestLikeCreation:
    @pytest.mark.asyncio
    async def test_duplicate_like_is_idempotent(self):
        me = _me()
        target_id = str(ObjectId())
        users = _users_col(target_doc={"_id": ObjectId(target_id)})
        existing = {"from_user_id": str(me["_id"]), "to_user_id": target_id}
        likes = _likes_col(existing_self_like=existing)

        with (
            patch("app.routers.likes.get_users_collection", return_value=users),
            patch("app.routers.likes.get_likes_collection", return_value=likes),
        ):
            result = await like_user(user_id=target_id, current_user=me)

        assert result == {"matched": False, "match_id": None}
        likes.insert_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_one_sided_like_inserts_without_match(self):
        me = _me()
        target_id = str(ObjectId())
        users = _users_col(target_doc={"_id": ObjectId(target_id)})
        likes = _likes_col()

        with (
            patch("app.routers.likes.get_users_collection", return_value=users),
            patch("app.routers.likes.get_likes_collection", return_value=likes),
        ):
            result = await like_user(user_id=target_id, current_user=me)

        likes.insert_one.assert_awaited_once()
        assert result == {"matched": False, "match_id": None}


# ===========================================================================
# Match creation
# ===========================================================================

class TestMatchCreation:
    @pytest.mark.asyncio
    async def test_mutual_like_creates_match(self):
        me = _me()
        target_id = str(ObjectId())
        users = _users_col(target_doc={"_id": ObjectId(target_id)})
        reverse = {"from_user_id": target_id, "to_user_id": str(me["_id"])}
        likes = _likes_col(reverse_like=reverse)
        new_match_id = ObjectId()
        matches = _matches_col(existing_match=None, inserted_id=new_match_id)

        with (
            patch("app.routers.likes.get_users_collection", return_value=users),
            patch("app.routers.likes.get_likes_collection", return_value=likes),
            patch("app.routers.likes.get_matches_collection", return_value=matches),
        ):
            result = await like_user(user_id=target_id, current_user=me)

        matches.insert_one.assert_awaited_once()
        inserted_doc = matches.insert_one.await_args[0][0]
        assert sorted(inserted_doc["user_ids"]) == sorted([str(me["_id"]), target_id])
        assert inserted_doc["seen_by"] == []
        assert result == {"matched": True, "match_id": str(new_match_id)}

    @pytest.mark.asyncio
    async def test_mutual_like_idempotent_when_match_already_exists(self):
        me = _me()
        target_id = str(ObjectId())
        users = _users_col(target_doc={"_id": ObjectId(target_id)})
        reverse = {"from_user_id": target_id, "to_user_id": str(me["_id"])}
        likes = _likes_col(reverse_like=reverse)
        existing_match_id = ObjectId()
        matches = _matches_col(existing_match={"_id": existing_match_id})

        with (
            patch("app.routers.likes.get_users_collection", return_value=users),
            patch("app.routers.likes.get_likes_collection", return_value=likes),
            patch("app.routers.likes.get_matches_collection", return_value=matches),
        ):
            result = await like_user(user_id=target_id, current_user=me)

        matches.insert_one.assert_not_called()
        assert result == {"matched": True, "match_id": str(existing_match_id)}


# ===========================================================================
# Unlike
# ===========================================================================

class TestUnlike:
    @pytest.mark.asyncio
    async def test_delete_called_with_correct_keys(self):
        me = _me()
        target_id = str(ObjectId())
        likes = _likes_col()

        with patch("app.routers.likes.get_likes_collection", return_value=likes):
            result = await unlike_user(user_id=target_id, current_user=me)

        likes.delete_one.assert_awaited_once_with(
            {"from_user_id": str(me["_id"]), "to_user_id": target_id}
        )
        assert result == {"detail": "Like removed"}

    @pytest.mark.asyncio
    async def test_safe_when_no_matching_like_exists(self):
        me = _me()
        likes = _likes_col()
        likes.delete_one = AsyncMock(return_value=MagicMock(deleted_count=0))

        with patch("app.routers.likes.get_likes_collection", return_value=likes):
            result = await unlike_user(user_id=str(ObjectId()), current_user=me)

        assert result == {"detail": "Like removed"}
