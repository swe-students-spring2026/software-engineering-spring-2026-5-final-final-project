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