"""
Tests for Spotify OAuth flow.

Covers:
- /api/spotify/connect  → redirect with correct state JWT
- /api/spotify/callback → happy path, bad state, Spotify error, token exchange failure
- /api/spotify/disconnect → clears tokens in DB

MongoDB is fully mocked via unittest.mock; no live DB or Spotify connection needed.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# App bootstrap (adjust import path if your entry point differs)
# ---------------------------------------------------------------------------
from app.main import app
from app.auth import encode_jwt

client = TestClient(app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

FAKE_USER_ID = str(ObjectId())

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


def _auth_cookie() -> dict:
    """Return a cookies dict with a valid vibe_token for FAKE_USER."""
    token = encode_jwt({"user_id": FAKE_USER_ID})
    return {"vibe_token": token}


# ---------------------------------------------------------------------------
# GET /api/spotify/connect
# ---------------------------------------------------------------------------


class TestSpotifyConnect:
    @patch("app.routers.spotify.get_current_user", return_value=FAKE_USER)
    @patch("app.services.spotify.get_authorization_url")
    def test_redirects_to_spotify(self, mock_auth_url, mock_get_user):
        """Should return a 307 redirect to the Spotify authorization URL."""
        mock_auth_url.return_value = "https://accounts.spotify.com/authorize?fake=1"

        response = client.get(
            "/api/spotify/connect",
            cookies=_auth_cookie(),
            allow_redirects=False,
        )

        assert response.status_code in (302, 307)
        assert "accounts.spotify.com" in response.headers["location"]

    @patch("app.routers.spotify.get_current_user", return_value=FAKE_USER)
    @patch("app.services.spotify.get_authorization_url")
    def test_state_param_is_embedded_in_url(self, mock_auth_url, mock_get_user):
        """get_authorization_url should be called with a non-empty state string."""
        mock_auth_url.return_value = "https://accounts.spotify.com/authorize?state=xyz"

        client.get(
            "/api/spotify/connect",
            cookies=_auth_cookie(),
            allow_redirects=False,
        )

        mock_auth_url.assert_called_once()
        _, kwargs = mock_auth_url.call_args
        state_value = kwargs.get("state") or mock_auth_url.call_args[0][0]
        assert state_value  # must be a non-empty string


# ---------------------------------------------------------------------------
# GET /api/spotify/callback
# ---------------------------------------------------------------------------


class TestSpotifyCallback:
    def _valid_state(self) -> str:
        return encode_jwt({"user_id": FAKE_USER_ID}, expiry_minutes=10)

    @patch("app.services.spotify.exchange_code_for_tokens", new_callable=AsyncMock)
    def test_happy_path_redirects_to_profile_setup(self, mock_exchange):
        """Valid code + valid state should store tokens and redirect."""
        mock_exchange.return_value = {
            "access_token": "acc",
            "refresh_token": "ref",
            "expires_at": 9999999999,
        }

        response = client.get(
            "/api/spotify/callback",
            params={"code": "spotify_code_123", "state": self._valid_state()},
            allow_redirects=False,
        )

        assert response.status_code in (302, 307)
        assert "/profile/setup" in response.headers["location"]
        mock_exchange.assert_awaited_once_with(
            user_id=FAKE_USER_ID, code="spotify_code_123"
        )

    def test_spotify_error_param_returns_400(self):
        """If Spotify sends back an error query param, return 400."""
        response = client.get(
            "/api/spotify/callback",
            params={
                "code": "",
                "state": self._valid_state(),
                "error": "access_denied",
            },
        )
        assert response.status_code == 400
        assert "access_denied" in response.json()["detail"]

    def test_invalid_state_returns_400(self):
        """A tampered or expired state JWT should return 400."""
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
    def test_token_exchange_failure_returns_502(self, mock_exchange):
        """If the Spotify token exchange throws, return 502."""
        response = client.get(
            "/api/spotify/callback",
            params={"code": "bad_code", "state": self._valid_state()},
        )
        assert response.status_code == 502

    def test_missing_code_returns_422(self):
        """Missing required `code` query param should fail validation."""
        response = client.get(
            "/api/spotify/callback",
            params={"state": self._valid_state()},
        )
        assert response.status_code == 422

    def test_missing_state_returns_422(self):
        """Missing required `state` query param should fail validation."""
        response = client.get(
            "/api/spotify/callback",
            params={"code": "some_code"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/spotify/disconnect
# ---------------------------------------------------------------------------


class TestSpotifyDisconnect:
    @patch("app.routers.spotify.get_current_user", return_value=FAKE_USER)
    @patch("app.services.spotify.disconnect_spotify", new_callable=AsyncMock)
    def test_disconnect_returns_200(self, mock_disconnect, mock_get_user):
        """Disconnect should call the service and return 200."""
        response = client.post(
            "/api/spotify/disconnect",
            cookies=_auth_cookie(),
        )

        assert response.status_code == 200
        assert "disconnected" in response.json()["detail"].lower()
        mock_disconnect.assert_awaited_once_with(user_id=FAKE_USER_ID)

    def test_disconnect_without_auth_returns_401(self):
        """Unauthenticated request should be rejected."""
        response = client.post("/api/spotify/disconnect")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Service-layer unit tests (no HTTP)
# ---------------------------------------------------------------------------


class TestGetAuthorizationUrl:
    @patch("app.services.spotify.SpotifyOAuth")
    def test_returns_url_string(self, mock_oauth_cls):
        from app.services.spotify import get_authorization_url

        mock_oauth = MagicMock()
        mock_oauth.get_authorize_url.return_value = "https://accounts.spotify.com/authorize?q=1"
        mock_oauth_cls.return_value = mock_oauth

        url = get_authorization_url(state="some_state")

        assert url.startswith("https://")
        mock_oauth.get_authorize_url.assert_called_once()

    @patch("app.services.spotify.SpotifyOAuth")
    def test_state_passed_to_oauth(self, mock_oauth_cls):
        from app.services.spotify import get_authorization_url

        mock_oauth = MagicMock()
        mock_oauth.get_authorize_url.return_value = "https://accounts.spotify.com/auth"
        mock_oauth_cls.return_value = mock_oauth

        get_authorization_url(state="my_state_token")

        call_kwargs = mock_oauth_cls.call_args.kwargs
        assert call_kwargs.get("state") == "my_state_token"


class TestExchangeCodeForTokens:
    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    @patch("app.services.spotify.SpotifyOAuth")
    async def test_stores_tokens_in_db(self, mock_oauth_cls, mock_get_col):
        from app.services.spotify import exchange_code_for_tokens

        # Mock OAuth token exchange
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = {
            "access_token": "acc_token",
            "refresh_token": "ref_token",
            "expires_at": 9999999999,
        }
        mock_oauth_cls.return_value = mock_oauth

        # Mock DB collection
        mock_col = AsyncMock()
        mock_get_col.return_value = mock_col

        result = await exchange_code_for_tokens(user_id=FAKE_USER_ID, code="auth_code")

        assert result["access_token"] == "acc_token"
        mock_col.update_one.assert_awaited_once()
        update_doc = mock_col.update_one.call_args[0][1]
        assert update_doc["$set"]["spotify.access_token"] == "acc_token"
        assert update_doc["$set"]["is_spotify_connected"] is True

    @pytest.mark.asyncio
    @patch("app.services.spotify.SpotifyOAuth")
    async def test_raises_runtime_error_on_failure(self, mock_oauth_cls):
        from app.services.spotify import exchange_code_for_tokens

        mock_oauth = MagicMock()
        mock_oauth.get_access_token.side_effect = Exception("Spotify down")
        mock_oauth_cls.return_value = mock_oauth

        with pytest.raises(RuntimeError, match="Failed to exchange"):
            await exchange_code_for_tokens(user_id=FAKE_USER_ID, code="bad_code")


class TestDisconnectSpotify:
    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    async def test_clears_tokens_and_sets_disconnected(self, mock_get_col):
        from app.services.spotify import disconnect_spotify

        mock_col = AsyncMock()
        mock_get_col.return_value = mock_col

        await disconnect_spotify(user_id=FAKE_USER_ID)

        mock_col.update_one.assert_awaited_once()
        update_doc = mock_col.update_one.call_args[0][1]
        assert update_doc["$set"]["spotify.access_token"] is None
        assert update_doc["$set"]["spotify.refresh_token"] is None
        assert update_doc["$set"]["is_spotify_connected"] is False


# ---------------------------------------------------------------------------
# Pure helper unit tests (no I/O)
# ---------------------------------------------------------------------------


class TestExtractTopArtists:
    def test_extracts_id_and_name(self):
        from app.services.spotify import _extract_top_artists

        raw = [
            {"id": "a1", "name": "Artist One", "genres": ["pop"], "popularity": 80},
            {"id": "a2", "name": "Artist Two", "genres": ["rock"], "popularity": 70},
        ]
        result = _extract_top_artists(raw)
        assert result == [{"id": "a1", "name": "Artist One"}, {"id": "a2", "name": "Artist Two"}]

    def test_empty_list_returns_empty(self):
        from app.services.spotify import _extract_top_artists

        assert _extract_top_artists([]) == []


class TestExtractTopGenres:
    def test_flattens_and_deduplicates(self):
        from app.services.spotify import _extract_top_genres

        raw = [
            {"id": "a1", "genres": ["pop", "dance pop"]},
            {"id": "a2", "genres": ["pop", "indie"]},   # "pop" is a duplicate
            {"id": "a3", "genres": []},
        ]
        result = _extract_top_genres(raw)
        assert result == ["pop", "dance pop", "indie"]

    def test_preserves_first_seen_order(self):
        from app.services.spotify import _extract_top_genres

        raw = [
            {"genres": ["c", "a"]},
            {"genres": ["b", "c"]},
        ]
        assert _extract_top_genres(raw) == ["c", "a", "b"]

    def test_empty_artists_returns_empty(self):
        from app.services.spotify import _extract_top_genres

        assert _extract_top_genres([]) == []

    def test_artists_with_no_genres_key(self):
        from app.services.spotify import _extract_top_genres

        # Some artist objects may lack the 'genres' key entirely
        raw = [{"id": "a1"}, {"id": "a2", "genres": ["jazz"]}]
        assert _extract_top_genres(raw) == ["jazz"]


class TestAverageAudioFeatures:
    def test_averages_all_four_keys(self):
        from app.services.spotify import _average_audio_features

        features = [
            {"energy": 0.8, "valence": 0.6, "danceability": 0.7, "tempo": 120.0},
            {"energy": 0.4, "valence": 0.2, "danceability": 0.3, "tempo": 100.0},
        ]
        result = _average_audio_features(features)
        assert result == {
            "energy": 0.6,
            "valence": 0.4,
            "danceability": 0.5,
            "tempo": 110.0,
        }

    def test_skips_none_entries(self):
        from app.services.spotify import _average_audio_features

        features = [
            None,
            {"energy": 1.0, "valence": 1.0, "danceability": 1.0, "tempo": 200.0},
            None,
        ]
        result = _average_audio_features(features)
        assert result == {"energy": 1.0, "valence": 1.0, "danceability": 1.0, "tempo": 200.0}

    def test_all_none_returns_none(self):
        from app.services.spotify import _average_audio_features

        assert _average_audio_features([None, None]) is None

    def test_empty_list_returns_none(self):
        from app.services.spotify import _average_audio_features

        assert _average_audio_features([]) is None


# ---------------------------------------------------------------------------
# pull_user_data integration tests (mocked I/O)
# ---------------------------------------------------------------------------

# Reusable fake Spotify API responses
FAKE_ARTISTS = [
    {"id": "art1", "name": "Alpha", "genres": ["indie", "rock"]},
    {"id": "art2", "name": "Beta",  "genres": ["rock", "alternative"]},
]

FAKE_TRACKS = [{"id": "t1"}, {"id": "t2"}]

FAKE_AUDIO_FEATURES = [
    {"energy": 0.9, "valence": 0.7, "danceability": 0.8, "tempo": 130.0},
    {"energy": 0.5, "valence": 0.3, "danceability": 0.4, "tempo": 90.0},
]


def _make_mock_sp(artists=None, tracks=None, audio_features=None):
    """Build a MagicMock Spotify client with preset return values."""
    mock_sp = MagicMock()
    mock_sp.current_user_top_artists.return_value = {
        "items": artists if artists is not None else FAKE_ARTISTS
    }
    mock_sp.current_user_top_tracks.return_value = {
        "items": tracks if tracks is not None else FAKE_TRACKS
    }
    mock_sp.audio_features.return_value = (
        audio_features if audio_features is not None else FAKE_AUDIO_FEATURES
    )
    return mock_sp


class TestPullUserData:
    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    @patch("app.services.spotify._build_spotify_client")
    async def test_happy_path_persists_all_fields(self, mock_build_sp, mock_get_col):
        from app.services.spotify import pull_user_data

        # DB: find_one returns a user with a token; update_one is a no-op
        mock_col = AsyncMock()
        mock_col.find_one.return_value = {
            "_id": FAKE_USER_ID,
            "spotify": {"access_token": "valid_token"},
        }
        mock_get_col.return_value = mock_col
        mock_build_sp.return_value = _make_mock_sp()

        await pull_user_data(user_id=FAKE_USER_ID)

        mock_col.update_one.assert_awaited_once()
        update_doc = mock_col.update_one.call_args[0][1]["$set"]

        assert update_doc["spotify.top_artists"] == [
            {"id": "art1", "name": "Alpha"},
            {"id": "art2", "name": "Beta"},
        ]
        assert update_doc["spotify.top_genres"] == ["indie", "rock", "alternative"]
        assert update_doc["spotify.audio_features"] == {
            "energy": pytest.approx(0.7),
            "valence": pytest.approx(0.5),
            "danceability": pytest.approx(0.6),
            "tempo": pytest.approx(110.0),
        }
        assert "spotify.last_synced" in update_doc

    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    async def test_raises_if_no_access_token(self, mock_get_col):
        from app.services.spotify import pull_user_data

        mock_col = AsyncMock()
        mock_col.find_one.return_value = {
            "_id": FAKE_USER_ID,
            "spotify": {"access_token": None},
        }
        mock_get_col.return_value = mock_col

        with pytest.raises(RuntimeError, match="No Spotify access token"):
            await pull_user_data(user_id=FAKE_USER_ID)

    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    async def test_raises_if_user_not_found(self, mock_get_col):
        from app.services.spotify import pull_user_data

        mock_col = AsyncMock()
        mock_col.find_one.return_value = None
        mock_get_col.return_value = mock_col

        with pytest.raises(RuntimeError, match="No Spotify access token"):
            await pull_user_data(user_id=FAKE_USER_ID)

    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    @patch("app.services.spotify._build_spotify_client")
    async def test_audio_features_none_when_no_tracks(self, mock_build_sp, mock_get_col):
        """If the user has no top tracks, audio_features should be stored as None."""
        from app.services.spotify import pull_user_data

        mock_col = AsyncMock()
        mock_col.find_one.return_value = {
            "_id": FAKE_USER_ID,
            "spotify": {"access_token": "tok"},
        }
        mock_get_col.return_value = mock_col
        mock_build_sp.return_value = _make_mock_sp(tracks=[])  # empty track list

        await pull_user_data(user_id=FAKE_USER_ID)

        update_doc = mock_col.update_one.call_args[0][1]["$set"]
        assert update_doc["spotify.audio_features"] is None

    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    @patch("app.services.spotify._build_spotify_client")
    async def test_raises_runtime_error_on_spotify_exception(self, mock_build_sp, mock_get_col):
        """Any Spotify API error should be wrapped in RuntimeError."""
        from app.services.spotify import pull_user_data

        mock_col = AsyncMock()
        mock_col.find_one.return_value = {
            "_id": FAKE_USER_ID,
            "spotify": {"access_token": "tok"},
        }
        mock_get_col.return_value = mock_col

        mock_sp = MagicMock()
        mock_sp.current_user_top_artists.side_effect = Exception("Spotify 503")
        mock_build_sp.return_value = mock_sp

        with pytest.raises(RuntimeError, match="Failed to pull Spotify data"):
            await pull_user_data(user_id=FAKE_USER_ID)

    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    @patch("app.services.spotify._build_spotify_client")
    async def test_uses_correct_spotify_api_params(self, mock_build_sp, mock_get_col):
        """Verify the correct time_range and limit are passed to Spotify."""
        from app.services.spotify import pull_user_data

        mock_col = AsyncMock()
        mock_col.find_one.return_value = {
            "_id": FAKE_USER_ID,
            "spotify": {"access_token": "tok"},
        }
        mock_get_col.return_value = mock_col
        mock_sp = _make_mock_sp()
        mock_build_sp.return_value = mock_sp

        await pull_user_data(user_id=FAKE_USER_ID)

        mock_sp.current_user_top_artists.assert_called_once_with(
            limit=50, time_range="long_term"
        )
        mock_sp.current_user_top_tracks.assert_called_once_with(
            limit=50, time_range="medium_term"
        )


# ---------------------------------------------------------------------------
# refresh_token tests
# ---------------------------------------------------------------------------


class TestRefreshToken:
    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    @patch("app.services.spotify.SpotifyOAuth")
    async def test_happy_path_returns_new_access_token(self, mock_oauth_cls, mock_get_col):
        from app.services.spotify import refresh_token

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

        result = await refresh_token(user_id=FAKE_USER_ID)

        assert result == "new_access"
        mock_oauth.refresh_access_token.assert_called_once_with("old_refresh")

        update_doc = mock_col.update_one.call_args[0][1]["$set"]
        assert update_doc["spotify.access_token"] == "new_access"
        assert "spotify.refresh_token" not in update_doc  # not rotated

    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    @patch("app.services.spotify.SpotifyOAuth")
    async def test_rotated_refresh_token_is_persisted(self, mock_oauth_cls, mock_get_col):
        """If Spotify returns a new refresh_token, it should be saved."""
        from app.services.spotify import refresh_token

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

        await refresh_token(user_id=FAKE_USER_ID)

        update_doc = mock_col.update_one.call_args[0][1]["$set"]
        assert update_doc["spotify.refresh_token"] == "rotated_refresh"

    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    async def test_raises_if_no_refresh_token(self, mock_get_col):
        from app.services.spotify import refresh_token

        mock_col = AsyncMock()
        mock_col.find_one.return_value = {
            "_id": FAKE_USER_ID,
            "spotify": {"refresh_token": None},
        }
        mock_get_col.return_value = mock_col

        with pytest.raises(RuntimeError, match="No refresh token"):
            await refresh_token(user_id=FAKE_USER_ID)

    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    async def test_raises_if_user_not_found(self, mock_get_col):
        from app.services.spotify import refresh_token

        mock_col = AsyncMock()
        mock_col.find_one.return_value = None
        mock_get_col.return_value = mock_col

        with pytest.raises(RuntimeError, match="No refresh token"):
            await refresh_token(user_id=FAKE_USER_ID)

    @pytest.mark.asyncio
    @patch("app.services.spotify.get_users_collection")
    @patch("app.services.spotify.SpotifyOAuth")
    async def test_raises_runtime_error_on_spotify_failure(self, mock_oauth_cls, mock_get_col):
        from app.services.spotify import refresh_token

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
            await refresh_token(user_id=FAKE_USER_ID)


# ---------------------------------------------------------------------------
# scheduler tests
# ---------------------------------------------------------------------------


class TestScheduler:
    def test_start_creates_scheduler_and_adds_job(self):
        """start_scheduler() should create an AsyncIOScheduler with the weekly job."""
        from app.services import scheduler as sched_module

        # Ensure we start from a clean state
        sched_module._scheduler = None

        with patch("app.services.scheduler.AsyncIOScheduler") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance

            sched_module.start_scheduler()

            mock_instance.add_job.assert_called_once()
            job_kwargs = mock_instance.add_job.call_args
            # Verify the job function and id
            assert job_kwargs[1].get("id") == "weekly_spotify_refresh" or \
                   job_kwargs[0][0].__name__ == "_refresh_all_users"
            mock_instance.start.assert_called_once()

            # Cleanup
            sched_module._scheduler = None

    def test_start_is_idempotent(self):
        """Calling start_scheduler() twice should not create a second scheduler."""
        from app.services import scheduler as sched_module

        sched_module._scheduler = MagicMock()  # Simulate already-started state

        with patch("app.services.scheduler.AsyncIOScheduler") as mock_cls:
            sched_module.start_scheduler()
            mock_cls.assert_not_called()  # Should not create a new instance

        sched_module._scheduler = None

    def test_stop_shuts_down_and_clears(self):
        from app.services import scheduler as sched_module

        mock_sched = MagicMock()
        sched_module._scheduler = mock_sched

        sched_module.stop_scheduler()

        mock_sched.shutdown.assert_called_once_with(wait=False)
        assert sched_module._scheduler is None

    @pytest.mark.asyncio
    @patch("app.services.scheduler.pull_user_data", new_callable=AsyncMock)
    @patch("app.services.scheduler.refresh_token", new_callable=AsyncMock)
    @patch("app.services.scheduler.get_users_collection")
    async def test_refresh_all_users_calls_both_steps(
        self, mock_get_col, mock_refresh, mock_pull
    ):
        """_refresh_all_users should call refresh_token then pull_user_data per user."""
        from app.services.scheduler import _refresh_all_users

        # Mock async cursor
        mock_col = MagicMock()
        mock_col.find.return_value.__aiter__ = AsyncMock(
            return_value=iter([{"_id": "user1"}, {"_id": "user2"}])
        )
        mock_get_col.return_value = mock_col
        mock_refresh.return_value = "fresh_token"

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
        """A failure on one user should not prevent processing of remaining users."""
        from app.services.scheduler import _refresh_all_users

        mock_col = MagicMock()
        mock_col.find.return_value.__aiter__ = AsyncMock(
            return_value=iter([{"_id": "user1"}, {"_id": "user2"}])
        )
        mock_get_col.return_value = mock_col

        # user1's refresh fails; user2 should still be processed
        mock_refresh.side_effect = [RuntimeError("token expired"), "fresh_token"]

        await _refresh_all_users()

        # user2's pull should still be called
        mock_pull.assert_awaited_once_with(user_id="user2", access_token="fresh_token")