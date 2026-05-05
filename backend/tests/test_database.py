"""
Tests for app/database.py.

Covers:
- get_client()            singleton creation and reuse
- get_database()          correct database name ("vibe")
- get_users_collection()  correct collection name ("users")
- get_likes_collection()  correct collection name ("likes")
- get_matches_collection() correct collection name ("matches")
- create_indexes()        all six indexes with correct keys and options

No live MongoDB connection is required — AsyncIOMotorClient is fully mocked.
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
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

import app.database as db_module
from app.database import (
    create_indexes,
    get_client,
    get_database,
    get_likes_collection,
    get_matches_collection,
    get_users_collection,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the module-level _client singleton before and after every test."""
    db_module._client = None
    yield
    db_module._client = None


# ===========================================================================
# get_client
# ===========================================================================


class TestGetClient:
    def test_creates_motor_client_on_first_call(self):
        with patch("app.database.AsyncIOMotorClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            get_client()
            mock_cls.assert_called_once()

    def test_passes_mongodb_uri_to_client(self):
        with patch("app.database.AsyncIOMotorClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            get_client()
            uri_arg = mock_cls.call_args[0][0]
            assert uri_arg == get_settings().mongodb_uri

    def test_returns_the_created_client_instance(self):
        fake_client = MagicMock()
        with patch("app.database.AsyncIOMotorClient", return_value=fake_client):
            result = get_client()
        assert result is fake_client

    def test_second_call_returns_same_instance(self):
        with patch("app.database.AsyncIOMotorClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            first = get_client()
            second = get_client()
            assert first is second

    def test_client_instantiated_only_once_across_multiple_calls(self):
        with patch("app.database.AsyncIOMotorClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            get_client()
            get_client()
            get_client()
            mock_cls.assert_called_once()

    def test_stores_client_in_module_global(self):
        fake_client = MagicMock()
        with patch("app.database.AsyncIOMotorClient", return_value=fake_client):
            get_client()
        assert db_module._client is fake_client

    def test_new_client_created_after_singleton_reset(self):
        client_a, client_b = MagicMock(), MagicMock()
        with patch("app.database.AsyncIOMotorClient", side_effect=[client_a, client_b]):
            first = get_client()
            db_module._client = None
            second = get_client()
        assert first is client_a
        assert second is client_b
        assert first is not second


# ===========================================================================
# get_database
# ===========================================================================


class TestGetDatabase:
    def test_requests_vibe_database_from_client(self):
        mock_client = MagicMock()
        with patch("app.database.get_client", return_value=mock_client):
            get_database()
        mock_client.__getitem__.assert_called_once_with("vibe")

    def test_returns_result_of_client_subscript(self):
        mock_client = MagicMock()
        expected_db = MagicMock()
        mock_client.__getitem__.return_value = expected_db
        with patch("app.database.get_client", return_value=mock_client):
            result = get_database()
        assert result is expected_db

    def test_delegates_to_get_client(self):
        mock_client = MagicMock()
        with patch("app.database.get_client", return_value=mock_client) as mock_fn:
            get_database()
        mock_fn.assert_called_once()


# ===========================================================================
# get_users_collection
# ===========================================================================


class TestGetUsersCollection:
    def test_requests_users_collection_from_database(self):
        mock_db = MagicMock()
        with patch("app.database.get_database", return_value=mock_db):
            get_users_collection()
        mock_db.__getitem__.assert_called_once_with("users")

    def test_returns_result_of_database_subscript(self):
        mock_db = MagicMock()
        expected_col = MagicMock()
        mock_db.__getitem__.return_value = expected_col
        with patch("app.database.get_database", return_value=mock_db):
            result = get_users_collection()
        assert result is expected_col

    def test_does_not_request_wrong_collection_name(self):
        mock_db = MagicMock()
        with patch("app.database.get_database", return_value=mock_db):
            get_users_collection()
        called_with = mock_db.__getitem__.call_args[0][0]
        assert called_with != "likes"
        assert called_with != "matches"


# ===========================================================================
# get_likes_collection
# ===========================================================================


class TestGetLikesCollection:
    def test_requests_likes_collection_from_database(self):
        mock_db = MagicMock()
        with patch("app.database.get_database", return_value=mock_db):
            get_likes_collection()
        mock_db.__getitem__.assert_called_once_with("likes")

    def test_returns_result_of_database_subscript(self):
        mock_db = MagicMock()
        expected_col = MagicMock()
        mock_db.__getitem__.return_value = expected_col
        with patch("app.database.get_database", return_value=mock_db):
            result = get_likes_collection()
        assert result is expected_col

    def test_does_not_request_wrong_collection_name(self):
        mock_db = MagicMock()
        with patch("app.database.get_database", return_value=mock_db):
            get_likes_collection()
        called_with = mock_db.__getitem__.call_args[0][0]
        assert called_with != "users"
        assert called_with != "matches"


# ===========================================================================
# get_matches_collection
# ===========================================================================


class TestGetMatchesCollection:
    def test_requests_matches_collection_from_database(self):
        mock_db = MagicMock()
        with patch("app.database.get_database", return_value=mock_db):
            get_matches_collection()
        mock_db.__getitem__.assert_called_once_with("matches")

    def test_returns_result_of_database_subscript(self):
        mock_db = MagicMock()
        expected_col = MagicMock()
        mock_db.__getitem__.return_value = expected_col
        with patch("app.database.get_database", return_value=mock_db):
            result = get_matches_collection()
        assert result is expected_col

    def test_does_not_request_wrong_collection_name(self):
        mock_db = MagicMock()
        with patch("app.database.get_database", return_value=mock_db):
            get_matches_collection()
        called_with = mock_db.__getitem__.call_args[0][0]
        assert called_with != "users"
        assert called_with != "likes"


# ===========================================================================
# create_indexes — helpers
# ===========================================================================


@pytest.fixture()
def mock_collections():
    """Return (mock_users, mock_likes, mock_matches) with patched accessors."""
    mu, ml, mm = AsyncMock(), AsyncMock(), AsyncMock()
    with (
        patch("app.database.get_users_collection", return_value=mu),
        patch("app.database.get_likes_collection", return_value=ml),
        patch("app.database.get_matches_collection", return_value=mm),
    ):
        yield mu, ml, mm


def _index_calls(mock_col) -> list[tuple]:
    """Return list of (key_arg, kwargs) for every create_index call on mock_col."""
    return [
        (c.args[0], c.kwargs)
        for c in mock_col.create_index.call_args_list
    ]


# ===========================================================================
# create_indexes — users
# ===========================================================================


class TestCreateIndexesUsers:
    @pytest.mark.asyncio
    async def test_creates_exactly_three_indexes_on_users(self, mock_collections):
        mu, _, _ = mock_collections
        await create_indexes()
        assert mu.create_index.await_count == 3

    @pytest.mark.asyncio
    async def test_email_index_is_unique(self, mock_collections):
        mu, _, _ = mock_collections
        await create_indexes()
        calls = _index_calls(mu)
        email_call = next(c for c in calls if c[0] == "email")
        assert email_call[1].get("unique") is True

    @pytest.mark.asyncio
    async def test_city_index_created(self, mock_collections):
        mu, _, _ = mock_collections
        await create_indexes()
        keys = [c[0] for c in _index_calls(mu)]
        assert "city" in keys

    @pytest.mark.asyncio
    async def test_city_index_is_not_unique(self, mock_collections):
        mu, _, _ = mock_collections
        await create_indexes()
        city_call = next(c for c in _index_calls(mu) if c[0] == "city")
        assert not city_call[1].get("unique")

    @pytest.mark.asyncio
    async def test_is_spotify_connected_index_created(self, mock_collections):
        mu, _, _ = mock_collections
        await create_indexes()
        keys = [c[0] for c in _index_calls(mu)]
        assert "is_spotify_connected" in keys

    @pytest.mark.asyncio
    async def test_is_spotify_connected_index_is_not_unique(self, mock_collections):
        mu, _, _ = mock_collections
        await create_indexes()
        sc_call = next(c for c in _index_calls(mu) if c[0] == "is_spotify_connected")
        assert not sc_call[1].get("unique")


# ===========================================================================
# create_indexes — likes
# ===========================================================================


class TestCreateIndexesLikes:
    @pytest.mark.asyncio
    async def test_creates_exactly_two_indexes_on_likes(self, mock_collections):
        _, ml, _ = mock_collections
        await create_indexes()
        assert ml.create_index.await_count == 2

    @pytest.mark.asyncio
    async def test_compound_index_key_structure(self, mock_collections):
        _, ml, _ = mock_collections
        await create_indexes()
        keys = [c[0] for c in _index_calls(ml)]
        assert [("from_user_id", 1), ("to_user_id", 1)] in keys

    @pytest.mark.asyncio
    async def test_compound_index_is_unique(self, mock_collections):
        _, ml, _ = mock_collections
        await create_indexes()
        compound_call = next(
            c for c in _index_calls(ml)
            if c[0] == [("from_user_id", 1), ("to_user_id", 1)]
        )
        assert compound_call[1].get("unique") is True

    @pytest.mark.asyncio
    async def test_to_user_id_index_created(self, mock_collections):
        _, ml, _ = mock_collections
        await create_indexes()
        keys = [c[0] for c in _index_calls(ml)]
        assert "to_user_id" in keys

    @pytest.mark.asyncio
    async def test_to_user_id_index_is_not_unique(self, mock_collections):
        _, ml, _ = mock_collections
        await create_indexes()
        tuid_call = next(c for c in _index_calls(ml) if c[0] == "to_user_id")
        assert not tuid_call[1].get("unique")


# ===========================================================================
# create_indexes — matches
# ===========================================================================


class TestCreateIndexesMatches:
    @pytest.mark.asyncio
    async def test_creates_exactly_one_index_on_matches(self, mock_collections):
        _, _, mm = mock_collections
        await create_indexes()
        assert mm.create_index.await_count == 1

    @pytest.mark.asyncio
    async def test_user_ids_index_created(self, mock_collections):
        _, _, mm = mock_collections
        await create_indexes()
        keys = [c[0] for c in _index_calls(mm)]
        assert "user_ids" in keys

    @pytest.mark.asyncio
    async def test_user_ids_index_is_not_unique(self, mock_collections):
        _, _, mm = mock_collections
        await create_indexes()
        mm.create_index.assert_awaited_once_with("user_ids")


# ===========================================================================
# create_indexes — cross-collection
# ===========================================================================


class TestCreateIndexesAll:
    @pytest.mark.asyncio
    async def test_total_index_count_is_six(self, mock_collections):
        mu, ml, mm = mock_collections
        await create_indexes()
        total = (
            mu.create_index.await_count
            + ml.create_index.await_count
            + mm.create_index.await_count
        )
        assert total == 6

    @pytest.mark.asyncio
    async def test_all_three_collections_are_indexed(self, mock_collections):
        mu, ml, mm = mock_collections
        await create_indexes()
        assert mu.create_index.called
        assert ml.create_index.called
        assert mm.create_index.called
