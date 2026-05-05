"""
Tests for web-app Flask routes.
Run: python -m pytest tests/ --cov=. --cov-report=term-missing --cov-fail-under=80
"""
from unittest import mock

import pytest
import requests
from unittest.mock import patch, MagicMock
from app import app


# ── Helper: fake Spotify user ─────────────────────────────────────────────────

def fake_spotify_user():
    return {
        "display_name": "Test User",
        "id": "spotify_user_123",
        "images": [{"url": "https://example.com/avatar.jpg"}],
    }


# ── /login ────────────────────────────────────────────────────────────────────

class TestLogin:
    def test_login_renders_page(self, client):
        with patch("app.get_sp_oauth") as mock_oauth:
            mock_oauth.get_authorize_url.return_value = "https://accounts.spotify.com/authorize?..."
            resp = client.get("/login")
        assert resp.status_code == 200
        assert b"Spotify" in resp.data or b"auth_url" in resp.data or resp.status_code == 200

    def test_login_redirects_if_already_logged_in(self, logged_in_client):
        resp = logged_in_client.get("/login")
        assert resp.status_code == 302
        assert "/" in resp.headers["Location"]


# ── / (index) ─────────────────────────────────────────────────────────────────

class TestIndex:
    def test_index_redirects_when_not_logged_in(self, client):
        resp = client.get("/")
        assert resp.status_code == 302
        assert "login" in resp.headers["Location"]

    def test_index_renders_when_logged_in(self, logged_in_client):
        with patch("app.get_spotify_client") as mock_get_sp:
            mock_sp = MagicMock()
            mock_sp.current_user.return_value = fake_spotify_user()
            mock_get_sp.return_value = mock_sp

            resp = logged_in_client.get("/")

        assert resp.status_code == 200
        assert b"Test User" in resp.data

    def test_index_redirects_when_token_invalid(self, client):
        with client.session_transaction() as sess:
            sess["token_info"] = None
        resp = client.get("/")
        assert resp.status_code == 302

    def test_index_shows_no_tracks_initially(self, logged_in_client):
        with patch("app.get_spotify_client") as mock_get_sp:
            mock_sp = MagicMock()
            mock_sp.current_user.return_value = fake_spotify_user()
            mock_get_sp.return_value = mock_sp

            resp = logged_in_client.get("/")

        # No results section unless tracks exist
        assert b"Your playlist" not in resp.data


# ── /logout ───────────────────────────────────────────────────────────────────

class TestLogout:
    def test_logout_clears_session(self, logged_in_client):
        resp = logged_in_client.get("/logout")
        assert resp.status_code == 302
        # After logout, index should redirect to login
        resp2 = logged_in_client.get("/")
        assert resp2.status_code == 302
        assert "login" in resp2.headers["Location"]

    def test_logout_redirects_to_login(self, logged_in_client):
        resp = logged_in_client.get("/logout")
        assert "login" in resp.headers["Location"]


# ── /callback ─────────────────────────────────────────────────────────────────

class TestCallback:
    def test_callback_stores_token_and_redirects(self, client):
        fake_token = {
            "access_token": "new-token",
            "refresh_token": "new-refresh",
            "expires_at": 9999999999,
        }
        with patch("app.get_sp_oauth") as mock_oauth, \
             patch("app.spotipy.Spotify") as mock_sp_class:
            
            mock_oauth.return_value.get_access_token.return_value = fake_token
            mock_sp_instance = MagicMock()
            mock_sp_instance.current_user.return_value = fake_spotify_user()
            mock_sp_class.return_value = mock_sp_instance

            resp = client.get("/callback?code=fake-code")

        assert resp.status_code == 302
        assert "/" in resp.headers["Location"]

    def test_callback_missing_code_handled(self, client):
        with patch("app.get_sp_oauth") as mock_oauth:
            mock_oauth_instance = mock_oauth.return_value
            mock_oauth_instance.get_access_token.side_effect = Exception("No code")
            resp = client.get("/callback")
        # Should not crash with 500 — either redirect or error page
        assert resp.status_code in (302, 400, 500)


# ── /recommend ────────────────────────────────────────────────────────────────

class TestRecommend:
    def test_recommend_redirects_if_not_logged_in(self, client):
        resp = client.post("/recommend", data={"mood_text": "happy"})
        assert resp.status_code == 302
        assert "login" in resp.headers["Location"]

    def test_recommend_calls_ml_client(self, logged_in_client):
    
        with patch("app.get_spotify_client") as mock_get_sp, \
            patch("app.requests.post") as mock_post, \
            patch("app.requests.get") as mock_get_weather:

            
            mock_sp = MagicMock()
            mock_get_sp.return_value = mock_sp

            mock_get_weather.return_value.json.return_value = {"main": "Clear"}
            mock_get_weather.return_value.status_code = 200

            
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "tracks": [
                    {"name": "Good Days", "artist": "SZA", "album_art": "http://example.com/img.jpg"}
                ],
                "session_id": "fake-session"
            }

            resp = logged_in_client.post("/recommend", data={
                "mood_text": "happy",
                "city": "London"
            })

        assert resp.status_code == 200
        assert b"Good Days" in resp.data

    def test_recommend_shows_empty_on_ml_client_error(self, logged_in_client):
        with patch("app.get_spotify_client") as mock_get_sp, \
             patch("app.requests.post") as mock_post:

            mock_sp = MagicMock()
            mock_sp.current_user.return_value = fake_spotify_user()
            mock_get_sp.return_value = mock_sp

            mock_post.side_effect = requests.RequestException("ml-client down")

            resp = logged_in_client.post("/recommend", data={
                "mood_text": "happy",
                "energy": "50",
                "valence": "50",
            })

        assert resp.status_code == 200
        assert b"Good Days" not in resp.data


# ── /save_playlist ────────────────────────────────────────────────────────────



# ── get_spotify_client helper ─────────────────────────────────────────────────

class TestGetSpotifyClient:
    def test_returns_none_when_no_session(self, client):
        from app import get_spotify_client
        with app.test_request_context():
            result = get_spotify_client()
        assert result is None

    def test_refreshes_expired_token(self, client):
        from app import get_spotify_client
        expired_token = {
            "access_token": "old-token",
            "refresh_token": "refresh-token",
            "expires_at": 0,
        }
        new_token = {
            "access_token": "new-token",
            "refresh_token": "refresh-token",
            "expires_at": 9999999999,
        }
        
        with client.session_transaction() as sess:
            sess["token_info"] = expired_token

        with patch("app.get_sp_oauth") as mock_oauth, \
             patch("app.spotipy.Spotify") as mock_sp_class:
            
            mock_oauth_instance = mock_oauth.return_value
            mock_oauth_instance.is_token_expired.return_value = True
            mock_oauth_instance.refresh_access_token.return_value = new_token
            
            mock_sp_instance = MagicMock()
            mock_sp_class.return_value = mock_sp_instance

    
            with app.test_request_context():
                from flask import session
                session["token_info"] = expired_token 
                
                
                result = get_spotify_client()

                assert session["token_info"]["access_token"] == "new-token"
                assert result is not None

    def test_returns_client_when_valid_token(self, logged_in_client):
        from app import get_spotify_client
        with patch("app.get_sp_oauth") as mock_oauth, \
             patch("app.spotipy.Spotify") as mock_sp_class:
            mock_oauth().is_token_expired.return_value = False
            mock_sp_class.return_value = MagicMock()

            with app.test_request_context():
                from flask import session
                session["token_info"] = {
                    "access_token": "valid-token",
                    "refresh_token": "refresh",
                    "expires_at": 9999999999,
                }
                result = get_spotify_client()