"""
Tests for Spotify OAuth flow, service helpers, and background scheduler.

Covers:
- app/routers/spotify.py  (connect / callback / disconnect endpoints)
- app/services/spotify.py (pure helpers + async service functions)
- app/services/scheduler.py (start/stop + weekly refresh job)

All MongoDB and Spotify API calls are mocked via unittest.mock.
No live DB or Spotify connection is required to run this suite.
"""

# ---------------------------------------------------------------------------
# Env-var bootstrap — MUST come before any app.* import so pydantic
# BaseSettings picks up the values on first instantiation.
# ---------------------------------------------------------------------------
import os

os.environ.setdefault("SPOTIFY_CLIENT_ID", "test_spotify_client_id")
os.environ.setdefault("SPOTIFY_CLIENT_SECRET", "test_spotify_client_secret")
os.environ.setdefault("SPOTIFY_REDIRECT_URI", "http://localhost:8000/api/spotify/callback")
os.environ.setdefault("JWT_SECRET", "testsecret_32_bytes_minimum_key!!")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

# Clear the lru_cache so Settings re-reads the env vars we just set above
from app.config import get_settings
get_settings.cache_clear()

# ---------------------------------------------------------------------------
# Standard imports
# ---------------------------------------------------------------------------
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import encode_jwt, get_current_user
from app.routers import spotify as spotify_router
from app.services import spotify as spotify_service
from app.services.spotify import (
    _average_audio_features,
    _extract_top_artists,
    _extract_top_genres,
)

# ---------------------------------------------------------------------------
# Shared test doubles
# ---------------------------------------------------------------------------

FAKE_USER_ID = "507f1f77bcf86cd799439011"  # valid 24-hex ObjectId string
FAKE_USER = {
    "_id": FAKE_USER_ID,
    "email": "michael@example.com",
    "display_name": "Michael",
    "is_spotify_connected": False,
    "spotify": {
        "access_token": None,
        "refresh_token": None,
        "top_artists": [],
        "top_genres": [],
        "audio_features": None,
        "last_synced": None,
    },
}

# Lightweight test app — no APScheduler lifespan, deterministic auth
_test_app = FastAPI()
_test_app.include_router(spotify_router.router)
_test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

client = TestClient(_test_app, raise_server_exceptions=False)


def _valid_state() -> str:
    """Return a freshly-signed state JWT for FAKE_USER_ID."""
    return encode_jwt({"user_id": FAKE_USER_ID}, expiry_minutes=10)


# ===========================================================================
# Router tests — GET /api/spotify/connect
# ===========================================================================


class TestSpotifyConnect:
    @patch(
        "app.services.spotify.get_authorization_url",
        return_value="https://accounts.spotify.com/authorize?fake=1",
    )
    def test_redirects_to_spotify(self, mock_auth_url):
        response = client.get("/api/spotify/connect", follow_redirects=False)

        assert response.status_code in (302, 307)
        assert "accounts.spotify.com" in response.headers["location"]

    @patch(
        "app.services.spotify.get_authorization_url",
        return_value="https://accounts.spotify.com/authorize?state=xyz",
    )
    def test_state_jwt_passed_to_authorization_url(self, _mock_auth_url):
        client.get("/api/spotify/connect", follow_redirects=False)

        _mock_auth_url.assert_called_once()
        state_arg = _mock_auth_url.call_args.kwargs.get(
            "state"
        ) or _mock_auth_url.call_args.args[0]
        assert state_arg  # non-empty string


# ===========================================================================
# Router tests — GET /api/spotify/callback
# ===========================================================================


class TestSpotifyCallback:
    @patch("app.services.spotify.pull_user_data", new_callable=AsyncMock)
    @patch("app.services.spotify.exchange_code_for_tokens", new_callable=AsyncMock)
    def test_happy_path_redirects_to_profile_setup(self, mock_exchange, mock_pull):
        mock_exchange.return_value = {
            "access_token": "acc_tok",
            "refresh_token": "ref_tok",
            "expires_at": 9_999_999_999,
        }

        response = client.get(
            "/api/spotify/callback",
            params={"code": "spotify_code_123", "state": _valid_state()},
            follow_redirects=False,
        )

        assert response.status_code in (302, 307)
        assert "/profile/setup" in response.headers["location"]
        mock_exchange.assert_awaited_once_with(
            user_id=FAKE_USER_ID, code="spotify_code_123"
        )
        mock_pull.assert_awaited_once_with(
            user_id=FAKE_USER_ID, access_token="acc_tok"
        )

    def test_spotify_error_param_returns_400(self):
        response = client.get(
            "/api/spotify/callback",
            params={
                "code": "ignored",
                "state": _valid_state(),
                "error": "access_denied",
            },
        )
        assert response.status_code == 400
        assert "access_denied" in response.json()["detail"]

    def test_invalid_state_jwt_returns_400(self):
        response = client.get(
            "/api/spotify/callback",
            params={"code": "some_code", "state": "totally.invalid.jwt"},
        )
        assert response.status_code == 400
        assert "state" in response.json()["detail"].lower()

    @patch(
        "app.services.spotify.exchange_code_for_tokens",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Token exchange failed"),
    )
    def test_token_exchange_failure_returns_502(self, _exchange):
        response = client.get(
            "/api/spotify/callback",
            params={"code": "bad_code", "state": _valid_state()},
        )
        assert response.status_code == 502

    @patch("app.services.spotify.pull_user_data", new_callable=AsyncMock)
    @patch("app.services.spotify.exchange_code_for_tokens", new_callable=AsyncMock)
    def test_pull_failure_is_non_fatal(self, mock_exchange, mock_pull):
        """pull_user_data RuntimeError must not prevent the redirect."""
        mock_exchange.return_value = {"access_token": "acc", "refresh_token": "ref"}
        mock_pull.side_effect = RuntimeError("Spotify 429")

        response = client.get(
            "/api/spotify/callback",
            params={"code": "code", "state": _valid_state()},
            follow_redirects=False,
        )

        assert response.status_code in (302, 307)

    def test_missing_code_returns_422(self):
        response = client.get(
            "/api/spotify/callback",
            params={"state": _valid_state()},
        )
        assert response.status_code == 422

    def test_missing_state_returns_422(self):
        response = client.get(
            "/api/spotify/callback",
            params={"code": "some_code"},
        )
        assert response.status_code == 422


# ===========================================================================
# Router tests — POST /api/spotify/disconnect
# ===========================================================================


class TestSpotifyDisconnect:
    @patch("app.services.spotify.disconnect_spotify", new_callable=AsyncMock)
    def test_disconnect_returns_200(self, mock_disconnect):
        response = client.post("/api/spotify/disconnect")

        assert response.status_code == 200
        assert "disconnected" in response.json()["detail"].lower()
        mock_disconnect.assert_awaited_once_with(user_id=FAKE_USER_ID)

    def test_disconnect_without_auth_returns_401(self):
        """Verify that the endpoint rejects requests when auth dependency raises."""
        no_auth_app = FastAPI()
        no_auth_app.include_router(spotify_router.router)
        from fastapi import HTTPException

        no_auth_app.dependency_overrides[get_current_user] = lambda: (_ for _ in ()).throw(
            HTTPException(status_code=401, detail="Not authenticated")
        )
        c = TestClient(no_auth_app, raise_server_exceptions=False)
        assert c.post("/api/spotify/disconnect").status_code == 401


# ===========================================================================
# Service — pure helper functions (no I/O)
# ===========================================================================


class TestExtractTopArtists:
    def test_extracts_id_and_name(self):
        raw = [
            {"id": "a1", "name": "Alpha", "genres": ["pop"], "popularity": 80},
            {"id": "a2", "name": "Beta", "genres": ["rock"], "popularity": 70},
        ]
        assert _extract_top_artists(raw) == [
            {"id": "a1", "name": "Alpha"},
            {"id": "a2", "name": "Beta"},
        ]

    def test_empty_list(self):
        assert _extract_top_artists([]) == []

    def test_extra_fields_ignored(self):
        raw = [{"id": "x", "name": "X", "followers": 1000, "href": "url"}]
        assert _extract_top_artists(raw) == [{"id": "x", "name": "X"}]


class TestExtractTopGenres:
    def test_flattens_and_deduplicates(self):
        raw = [
            {"genres": ["pop", "dance pop"]},
            {"genres": ["pop", "indie"]},  # "pop" is a duplicate
            {"genres": []},
        ]
        assert _extract_top_genres(raw) == ["pop", "dance pop", "indie"]

    def test_preserves_first_seen_order(self):
        raw = [{"genres": ["c", "a"]}, {"genres": ["b", "c"]}]
        assert _extract_top_genres(raw) == ["c", "a", "b"]

    def test_empty_artists(self):
        assert _extract_top_genres([]) == []

    def test_artist_missing_genres_key(self):
        raw = [{"id": "a1"}, {"id": "a2", "genres": ["jazz"]}]
        assert _extract_top_genres(raw) == ["jazz"]


class TestAverageAudioFeatures:
    def test_averages_all_four_keys(self):
        features = [
            {"energy": 0.8, "valence": 0.6, "danceability": 0.7, "tempo": 120.0},
            {"energy": 0.4, "valence": 0.2, "danceability": 0.3, "tempo": 100.0},
        ]
        result = _average_audio_features(features)
        assert result == pytest.approx(
            {"energy": 0.6, "valence": 0.4, "danceability": 0.5, "tempo": 110.0}
        )

    def test_skips_none_entries(self):
        features = [
            None,
            {"energy": 1.0, "valence": 1.0, "danceability": 1.0, "tempo": 200.0},
            None,
        ]
        result = _average_audio_features(features)
        assert result == pytest.approx(
            {"energy": 1.0, "valence": 1.0, "danceability": 1.0, "tempo": 200.0}
        )

    def test_all_none_returns_none(self):
        assert _average_audio_features([None, None]) is None

    def test_empty_list_returns_none(self):
        assert _average_audio_features([]) is None

    def test_single_track(self):
        f = {"energy": 0.5, "valence": 0.5, "danceability": 0.5, "tempo": 100.0}
        assert _average_audio_features([f]) == pytest.approx(f)


# ===========================================================================
# Service — _build_spotify_client
# ===========================================================================


class TestBuildSpotifyClient:
    @patch("app.services.spotify.spotipy.Spotify")
    def test_passes_access_token_as_auth(self, mock_spotify_cls):
        from app.services.spotify import _build_spotify_client

        mock_spotify_cls.return_value = MagicMock()
        _build_spotify_client("my_access_token")

        mock_spotify_cls.assert_called_once_with(auth="my_access_token")


# ===========================================================================
# Service — get_authorization_url
# ===========================================================================


class TestGetAuthorizationUrl:
    @patch("app.services.spotify.SpotifyOAuth")
    def test_returns_url_string(self, mock_oauth_cls):
        mock_oauth = MagicMock()
        mock_oauth.get_authorize_url.return_value = (
            "https://accounts.spotify.com/authorize?q=1"
        )
        mock_oauth_cls.return_value = mock_oauth

        url = spotify_service.get_authorization_url(state="some_state")

        assert url.startswith("https://")
        mock_oauth.get_authorize_url.assert_called_once()

    @patch("app.services.spotify.SpotifyOAuth")
    def test_state_forwarded_to_oauth_constructor(self, mock_oauth_cls):
        mock_oauth = MagicMock()
        mock_oauth.get_authorize_url.return_value = "https://accounts.spotify.com/auth"
        mock_oauth_cls.return_value = mock_oauth

        spotify_service.get_authorization_url(state="my_state_token")

        assert mock_oauth_cls.call_args.kwargs.get("state") == "my_state_token"


# ===========================================================================
# Service — exchange_code_for_tokens
# ===========================================================================


class TestExchangeCodeForTokens:
    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    @patch("app.services.spotify.SpotifyOAuth")
    async def test_stores_tokens_and_returns_token_info(self, mock_oauth_cls, mock_get_col):
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = {
            "access_token": "acc_token",
            "refresh_token": "ref_token",
            "expires_at": 9_999_999_999,
        }
        mock_oauth_cls.return_value = mock_oauth

        mock_col = AsyncMock()
        mock_get_col.return_value = mock_col

        result = await spotify_service.exchange_code_for_tokens(
            user_id=FAKE_USER_ID, code="auth_code"
        )

        assert result["access_token"] == "acc_token"
        mock_col.update_one.assert_awaited_once()
        set_doc = mock_col.update_one.call_args[0][1]["$set"]
        assert set_doc["spotify.access_token"] == "acc_token"
        assert set_doc["spotify.refresh_token"] == "ref_token"
        assert set_doc["is_spotify_connected"] is True

    @pytest.mark.asyncio
    @patch("app.services.spotify.SpotifyOAuth")
    async def test_raises_runtime_error_on_oauth_failure(self, mock_oauth_cls):
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.side_effect = Exception("Spotify down")
        mock_oauth_cls.return_value = mock_oauth

        with pytest.raises(RuntimeError, match="Failed to exchange"):
            await spotify_service.exchange_code_for_tokens(
                user_id=FAKE_USER_ID, code="bad_code"
            )


# ===========================================================================
# Service — refresh_token
# ===========================================================================


class TestRefreshToken:
    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    @patch("app.services.spotify.SpotifyOAuth")
    async def test_returns_new_access_token(self, mock_oauth_cls, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = {
            "_id": FAKE_USER_ID,
            "spotify": {"refresh_token": "old_refresh"},
        }
        mock_get_col.return_value = mock_col

        mock_oauth = MagicMock()
        mock_oauth.refresh_access_token.return_value = {
            "access_token": "new_access",
            "refresh_token": None,
        }
        mock_oauth_cls.return_value = mock_oauth

        result = await spotify_service.refresh_token(user_id=FAKE_USER_ID)

        assert result == "new_access"
        mock_oauth.refresh_access_token.assert_called_once_with("old_refresh")
        set_doc = mock_col.update_one.call_args[0][1]["$set"]
        assert set_doc["spotify.access_token"] == "new_access"
        assert "spotify.refresh_token" not in set_doc  # not rotated

    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    @patch("app.services.spotify.SpotifyOAuth")
    async def test_rotated_refresh_token_is_persisted(self, mock_oauth_cls, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = {
            "_id": FAKE_USER_ID,
            "spotify": {"refresh_token": "old_refresh"},
        }
        mock_get_col.return_value = mock_col

        mock_oauth = MagicMock()
        mock_oauth.refresh_access_token.return_value = {
            "access_token": "new_access",
            "refresh_token": "rotated_refresh",
        }
        mock_oauth_cls.return_value = mock_oauth

        await spotify_service.refresh_token(user_id=FAKE_USER_ID)

        set_doc = mock_col.update_one.call_args[0][1]["$set"]
        assert set_doc["spotify.refresh_token"] == "rotated_refresh"

    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    async def test_raises_if_no_refresh_token_stored(self, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = {
            "_id": FAKE_USER_ID,
            "spotify": {"refresh_token": None},
        }
        mock_get_col.return_value = mock_col

        with pytest.raises(RuntimeError, match="No refresh token"):
            await spotify_service.refresh_token(user_id=FAKE_USER_ID)

    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    async def test_raises_if_user_not_found(self, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = None
        mock_get_col.return_value = mock_col

        with pytest.raises(RuntimeError, match="No refresh token"):
            await spotify_service.refresh_token(user_id=FAKE_USER_ID)

    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    @patch("app.services.spotify.SpotifyOAuth")
    async def test_raises_runtime_error_on_spotify_failure(self, mock_oauth_cls, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = {
            "_id": FAKE_USER_ID,
            "spotify": {"refresh_token": "old_refresh"},
        }
        mock_get_col.return_value = mock_col

        mock_oauth = MagicMock()
        mock_oauth.refresh_access_token.side_effect = Exception("Spotify 401")
        mock_oauth_cls.return_value = mock_oauth

        with pytest.raises(RuntimeError, match="Failed to refresh"):
            await spotify_service.refresh_token(user_id=FAKE_USER_ID)


# ===========================================================================
# Service — disconnect_spotify
# ===========================================================================


class TestDisconnectSpotify:
    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    async def test_clears_tokens_and_marks_disconnected(self, mock_get_col):
        mock_col = AsyncMock()
        mock_get_col.return_value = mock_col

        await spotify_service.disconnect_spotify(user_id=FAKE_USER_ID)

        mock_col.update_one.assert_awaited_once()
        set_doc = mock_col.update_one.call_args[0][1]["$set"]
        assert set_doc["spotify.access_token"] is None
        assert set_doc["spotify.refresh_token"] is None
        assert set_doc["spotify.top_artists"] == []
        assert set_doc["spotify.top_genres"] == []
        assert set_doc["spotify.audio_features"] is None
        assert set_doc["is_spotify_connected"] is False


# ===========================================================================
# Service — pull_user_data
# ===========================================================================

_FAKE_RAW_ARTISTS = [
    {"id": "art1", "name": "Alpha", "genres": ["indie", "rock"]},
    {"id": "art2", "name": "Beta", "genres": ["rock", "alternative"]},
]
_FAKE_TRACKS = [{"id": "t1"}, {"id": "t2"}]
_FAKE_AUDIO_FEATURES = [
    {"energy": 0.9, "valence": 0.7, "danceability": 0.8, "tempo": 130.0},
    {"energy": 0.5, "valence": 0.3, "danceability": 0.4, "tempo": 90.0},
]


def _make_spotify_mock(
    artists=None, tracks=None, audio_features=None
) -> MagicMock:
    sp = MagicMock()
    sp.current_user_top_artists.return_value = {
        "items": artists if artists is not None else _FAKE_RAW_ARTISTS
    }
    sp.current_user_top_tracks.return_value = {
        "items": tracks if tracks is not None else _FAKE_TRACKS
    }
    sp.audio_features.return_value = (
        audio_features if audio_features is not None else _FAKE_AUDIO_FEATURES
    )
    return sp


class TestPullUserData:
    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    @patch("app.services.spotify._build_spotify_client")
    async def test_happy_path_persists_all_fields(self, mock_build, mock_get_col):
        mock_col = AsyncMock()
        mock_get_col.return_value = mock_col
        mock_build.return_value = _make_spotify_mock()

        await spotify_service.pull_user_data(
            user_id=FAKE_USER_ID, access_token="valid_tok"
        )

        mock_col.update_one.assert_awaited_once()
        set_doc = mock_col.update_one.call_args[0][1]["$set"]

        assert set_doc["spotify.top_artists"] == [
            {"id": "art1", "name": "Alpha"},
            {"id": "art2", "name": "Beta"},
        ]
        assert set_doc["spotify.top_genres"] == ["indie", "rock", "alternative"]
        assert set_doc["spotify.audio_features"] == pytest.approx(
            {"energy": 0.7, "valence": 0.5, "danceability": 0.6, "tempo": 110.0}
        )
        assert isinstance(set_doc["spotify.last_synced"], datetime)

    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    @patch("app.services.spotify._build_spotify_client")
    async def test_audio_features_none_when_no_tracks(self, mock_build, mock_get_col):
        mock_col = AsyncMock()
        mock_get_col.return_value = mock_col
        mock_build.return_value = _make_spotify_mock(tracks=[])

        await spotify_service.pull_user_data(
            user_id=FAKE_USER_ID, access_token="tok"
        )

        set_doc = mock_col.update_one.call_args[0][1]["$set"]
        assert set_doc["spotify.audio_features"] is None

    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    @patch("app.services.spotify._build_spotify_client")
    async def test_raises_runtime_error_on_spotify_exception(
        self, mock_build, mock_get_col
    ):
        mock_col = AsyncMock()
        mock_get_col.return_value = mock_col

        sp = MagicMock()
        sp.current_user_top_artists.side_effect = Exception("Spotify 503")
        mock_build.return_value = sp

        with pytest.raises(RuntimeError, match="Failed to pull Spotify data"):
            await spotify_service.pull_user_data(
                user_id=FAKE_USER_ID, access_token="tok"
            )

    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    @patch("app.services.spotify._build_spotify_client")
    async def test_correct_api_params_used(self, mock_build, mock_get_col):
        mock_col = AsyncMock()
        mock_get_col.return_value = mock_col
        sp = _make_spotify_mock()
        mock_build.return_value = sp

        await spotify_service.pull_user_data(
            user_id=FAKE_USER_ID, access_token="tok"
        )

        sp.current_user_top_artists.assert_called_once_with(
            limit=50, time_range="long_term"
        )
        sp.current_user_top_tracks.assert_called_once_with(
            limit=50, time_range="medium_term"
        )

    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    @patch("app.services.spotify._build_spotify_client")
    async def test_access_token_forwarded_to_client_builder(
        self, mock_build, mock_get_col
    ):
        mock_col = AsyncMock()
        mock_get_col.return_value = mock_col
        mock_build.return_value = _make_spotify_mock()

        await spotify_service.pull_user_data(
            user_id=FAKE_USER_ID, access_token="special_tok"
        )

        mock_build.assert_called_once_with("special_tok")


# ===========================================================================
# Scheduler tests
# ===========================================================================


class TestScheduler:
    def test_start_creates_scheduler_and_adds_weekly_job(self):
        from app.services import scheduler as sched_module

        sched_module._scheduler = None  # ensure clean state

        with patch("app.services.scheduler.AsyncIOScheduler") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance

            sched_module.start_scheduler()

            mock_instance.add_job.assert_called_once()
            job_id = mock_instance.add_job.call_args.kwargs.get("id")
            assert job_id == "weekly_spotify_refresh"
            mock_instance.start.assert_called_once()

            sched_module._scheduler = None  # cleanup

    def test_start_is_idempotent(self):
        from app.services import scheduler as sched_module

        sched_module._scheduler = MagicMock()  # already started

        with patch("app.services.scheduler.AsyncIOScheduler") as mock_cls:
            sched_module.start_scheduler()
            mock_cls.assert_not_called()

        sched_module._scheduler = None

    def test_stop_shuts_down_and_clears_reference(self):
        from app.services import scheduler as sched_module

        mock_sched = MagicMock()
        sched_module._scheduler = mock_sched

        sched_module.stop_scheduler()

        mock_sched.shutdown.assert_called_once_with(wait=False)
        assert sched_module._scheduler is None

    def test_stop_is_safe_when_not_started(self):
        from app.services import scheduler as sched_module

        sched_module._scheduler = None
        sched_module.stop_scheduler()  # must not raise

    @pytest.mark.asyncio
    @patch("app.services.scheduler.pull_user_data", new_callable=AsyncMock)
    @patch("app.services.scheduler.refresh_token", new_callable=AsyncMock)
    @patch("app.services.scheduler.get_users_collection")
    async def test_refresh_all_users_calls_both_steps_per_user(
        self, mock_get_col, mock_refresh, mock_pull
    ):
        from app.services.scheduler import _refresh_all_users

        mock_refresh.return_value = "fresh_token"

        # Async cursor mock
        class _AsyncCursor:
            def __aiter__(self):
                return self

            _items = iter([{"_id": "user1"}, {"_id": "user2"}])

            async def __anext__(self):
                try:
                    return next(self._items)
                except StopIteration:
                    raise StopAsyncIteration

        mock_col = MagicMock()
        mock_col.find.return_value = _AsyncCursor()
        mock_get_col.return_value = mock_col

        await _refresh_all_users()

        assert mock_refresh.await_count == 2
        assert mock_pull.await_count == 2
        mock_pull.assert_any_await(user_id="user1", access_token="fresh_token")
        mock_pull.assert_any_await(user_id="user2", access_token="fresh_token")

    @pytest.mark.asyncio
    @patch("app.services.scheduler.pull_user_data", new_callable=AsyncMock)
    @patch("app.services.scheduler.refresh_token", new_callable=AsyncMock)
    @patch("app.services.scheduler.get_users_collection")
    async def test_single_user_failure_does_not_stop_others(
        self, mock_get_col, mock_refresh, mock_pull
    ):
        from app.services.scheduler import _refresh_all_users

        class _AsyncCursor:
            def __aiter__(self):
                return self

            _items = iter([{"_id": "user1"}, {"_id": "user2"}])

            async def __anext__(self):
                try:
                    return next(self._items)
                except StopIteration:
                    raise StopAsyncIteration

        mock_col = MagicMock()
        mock_col.find.return_value = _AsyncCursor()
        mock_get_col.return_value = mock_col

        # user1's refresh fails; user2 must still be processed
        mock_refresh.side_effect = [RuntimeError("token expired"), "fresh_token"]

        await _refresh_all_users()

        mock_pull.assert_awaited_once_with(user_id="user2", access_token="fresh_token")
