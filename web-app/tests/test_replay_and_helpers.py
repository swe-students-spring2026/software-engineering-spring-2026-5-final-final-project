"""
Tests for the new functionality added in the history-replay PR:
  - _augment_mood helper
  - get_session_by_id helper
  - GET /history/<session_id> route
  - error branches in /recommend (weather fail, ML fail)
  - save_playlist failure paths
  - 404 handler

These complement tests/test_app.py and bring overall coverage above 80%.
"""
from unittest.mock import patch, MagicMock

import pytest
import requests
from bson.objectid import ObjectId

from app import app, _augment_mood, get_session_by_id


def fake_spotify_user():
    return {
        "display_name": "Test User",
        "id": "spotify_user_123",
        "images": [{"url": "https://example.com/avatar.jpg"}],
    }


# ── _augment_mood ─────────────────────────────────────────────────────────────

class TestAugmentMood:
    def test_returns_neutral_when_everything_blank(self):
        assert _augment_mood("", "", "50", "50") == "neutral"

    def test_uses_free_text_first(self):
        result = _augment_mood("missing my dog", "happy", "50", "50")
        assert "missing my dog" in result
        # mood_label should not also be in the prompt when free text exists
        assert "happy" not in result.lower().split("missing my dog")[1]

    def test_falls_back_to_label_when_no_free_text(self):
        assert _augment_mood("", "energized", "50", "50") == "energized"

    def test_high_energy_gets_high_energy_hint(self):
        result = _augment_mood("studying", "", "85", "50")
        assert "high energy" in result

    def test_low_energy_gets_mellow_hint(self):
        result = _augment_mood("studying", "", "15", "50")
        assert "low energy" in result or "mellow" in result

    def test_high_valence_gets_upbeat_hint(self):
        result = _augment_mood("studying", "", "50", "90")
        assert "upbeat" in result or "positive" in result

    def test_low_valence_gets_somber_hint(self):
        result = _augment_mood("studying", "", "50", "10")
        assert "somber" in result or "downcast" in result

    def test_middle_sliders_add_no_hints(self):
        result = _augment_mood("just chilling", "", "50", "50")
        assert result == "just chilling"

    def test_invalid_slider_values_default_to_neutral(self):
        # garbage strings shouldn't crash; should be treated as middle
        result = _augment_mood("test mood", "", "abc", "xyz")
        assert result == "test mood"

    def test_combines_text_and_extreme_sliders(self):
        result = _augment_mood("focused", "", "90", "85")
        assert "focused" in result
        assert "high energy" in result
        assert "upbeat" in result or "positive" in result


# ── get_session_by_id ─────────────────────────────────────────────────────────

class TestGetSessionById:
    def test_returns_none_when_no_user_id(self):
        assert get_session_by_id("anything", None) is None
        assert get_session_by_id("anything", "") is None

    def test_returns_none_when_no_session_id(self):
        assert get_session_by_id(None, "user1") is None
        assert get_session_by_id("", "user1") is None

    def test_returns_none_for_invalid_objectid(self):
        # garbage strings shouldn't blow up
        assert get_session_by_id("not-an-objectid", "user1") is None

    def test_queries_with_oid_and_user_id(self, mock_db):
        valid_oid = "650abc123def456789012345"
        expected_doc = {"_id": ObjectId(valid_oid), "user_id": "user1", "tracks": []}
        mock_db.sessions.find_one.return_value = expected_doc

        result = get_session_by_id(valid_oid, "user1")

        assert result == expected_doc
        mock_db.sessions.find_one.assert_called_once_with({
            "_id": ObjectId(valid_oid),
            "user_id": "user1",
        })


# ── GET /history/<session_id> ─────────────────────────────────────────────────

class TestReplaySession:
    def test_replay_redirects_when_not_logged_in(self, client):
        resp = client.get("/history/650abc123def456789012345")
        assert resp.status_code == 302
        assert "login" in resp.headers["Location"]

    def test_replay_returns_404_when_session_not_found(self, logged_in_client, mock_db):
        with patch("app.get_spotify_client") as mock_get_sp:
            mock_sp = MagicMock()
            mock_sp.current_user.return_value = fake_spotify_user()
            mock_get_sp.return_value = mock_sp
            mock_db.sessions.find_one.return_value = None  # no match

            resp = logged_in_client.get("/history/650abc123def456789012345")
        assert resp.status_code == 404

    def test_replay_returns_404_when_oid_invalid(self, logged_in_client):
        with patch("app.get_spotify_client") as mock_get_sp:
            mock_sp = MagicMock()
            mock_sp.current_user.return_value = fake_spotify_user()
            mock_get_sp.return_value = mock_sp

            resp = logged_in_client.get("/history/garbage")
        assert resp.status_code == 404

    def test_replay_renders_session_tracks(self, logged_in_client, mock_db):
        oid = ObjectId()
        past_session = {
            "_id": oid,
            "user_id": "test_user_123",
            "mood": "feeling reflective",
            "mood_label": "chill",
            "weather": {"temp": 20, "condition": "clear sky"},
            "tracks": [
                {"name": "Song A", "artist": "X", "uri": "spotify:track:1",
                 "external_url": "https://x"},
                {"name": "Song B", "artist": "Y", "uri": "spotify:track:2",
                 "external_url": "https://y"},
            ],
        }

        with patch("app.get_spotify_client") as mock_get_sp:
            mock_sp = MagicMock()
            mock_sp.current_user.return_value = fake_spotify_user()
            mock_get_sp.return_value = mock_sp
            mock_db.sessions.find_one.return_value = past_session
            mock_db.sessions.find.return_value.sort.return_value.limit.return_value = []

            resp = logged_in_client.get(f"/history/{oid}")

        assert resp.status_code == 200
        assert b"Song A" in resp.data
        assert b"Song B" in resp.data

    def test_replay_handles_missing_weather_gracefully(self, logged_in_client, mock_db):
        oid = ObjectId()
        past_session = {
            "_id": oid,
            "user_id": "test_user_123",
            "mood": "x",
            "mood_label": "",
            "weather": None,  # missing
            "tracks": [],
        }
        with patch("app.get_spotify_client") as mock_get_sp:
            mock_sp = MagicMock()
            mock_sp.current_user.return_value = fake_spotify_user()
            mock_get_sp.return_value = mock_sp
            mock_db.sessions.find_one.return_value = past_session
            mock_db.sessions.find.return_value.sort.return_value.limit.return_value = []

            resp = logged_in_client.get(f"/history/{oid}")
        assert resp.status_code == 200


# ── /recommend error branches ─────────────────────────────────────────────────

class TestRecommendErrors:
    def test_recommend_weather_fail_renders_index_with_flash(self, logged_in_client, mock_db):
        with patch("app.get_spotify_client") as mock_get_sp, \
             patch("app.requests.get") as mock_get:
            mock_sp = MagicMock()
            mock_sp.current_user.return_value = fake_spotify_user()
            mock_get_sp.return_value = mock_sp
            mock_get.side_effect = requests.RequestException("connection refused")
            mock_db.sessions.find.return_value.sort.return_value.limit.return_value = []

            resp = logged_in_client.post("/recommend", data={
                "mood_text": "feeling chill",
                "city_lat": "40.7128",
                "city_lon": "-74.0060",
                "city_name": "New York, NY",
                "energy": "50",
                "valence": "50",
            })

        assert resp.status_code == 200  # renders index, not 5xx

    def test_recommend_ml_fail_renders_index_with_flash(self, logged_in_client, mock_db):
        with patch("app.get_spotify_client") as mock_get_sp, \
             patch("app.requests.get") as mock_get, \
             patch("app.requests.post") as mock_post:
            mock_sp = MagicMock()
            mock_sp.current_user.return_value = fake_spotify_user()
            mock_get_sp.return_value = mock_sp

            weather_resp = MagicMock()
            weather_resp.json.return_value = {"temp": 20, "condition": "clear"}
            weather_resp.raise_for_status.return_value = None
            mock_get.return_value = weather_resp

            mock_post.side_effect = requests.RequestException("ML down")
            mock_db.sessions.find.return_value.sort.return_value.limit.return_value = []

            resp = logged_in_client.post("/recommend", data={
                "mood_text": "feeling chill",
                "city_lat": "40.7128",
                "city_lon": "-74.0060",
                "city_name": "New York, NY",
                "energy": "50",
                "valence": "50",
            })
        assert resp.status_code == 200

    def test_recommend_succeeds_with_tracks(self, logged_in_client, mock_db):
        with patch("app.get_spotify_client") as mock_get_sp, \
             patch("app.requests.get") as mock_get, \
             patch("app.requests.post") as mock_post:
            mock_sp = MagicMock()
            mock_sp.current_user.return_value = fake_spotify_user()
            mock_get_sp.return_value = mock_sp

            weather_resp = MagicMock()
            weather_resp.json.return_value = {"temp": 20, "condition": "clear"}
            weather_resp.raise_for_status.return_value = None
            mock_get.return_value = weather_resp

            ml_resp = MagicMock()
            ml_resp.json.return_value = {
                "tracks": [{"name": "Track A", "uri": "spotify:track:1"}],
                "session_id": "abc123",
            }
            ml_resp.raise_for_status.return_value = None
            mock_post.return_value = ml_resp

            mock_db.sessions.find.return_value.sort.return_value.limit.return_value = []

            resp = logged_in_client.post("/recommend", data={
                "mood_text": "feeling chill",
                "city_lat": "40.7128",
                "city_lon": "-74.0060",
                "city_name": "New York, NY",
                "energy": "50",
                "valence": "50",
            })
        assert resp.status_code == 200
        assert b"Track A" in resp.data


# ── /save_playlist error paths ────────────────────────────────────────────────

class TestSavePlaylistErrors:
    def test_save_playlist_redirects_when_not_logged_in(self, client):
        resp = client.post("/save_playlist", data={"track_ids": "spotify:track:1"})
        assert resp.status_code == 302
        assert "login" in resp.headers["Location"]

    def test_save_playlist_redirects_when_no_spotify(self, logged_in_client):
        with patch("app.get_spotify_client") as mock_get_sp:
            mock_get_sp.return_value = None
            resp = logged_in_client.post("/save_playlist",
                                          data={"track_ids": "spotify:track:1"})
        assert resp.status_code == 302
        assert "login" in resp.headers["Location"]

    def test_save_playlist_handles_empty_track_ids(self, logged_in_client):
        with patch("app.get_spotify_client") as mock_get_sp:
            mock_sp = MagicMock()
            mock_sp.current_user.return_value = fake_spotify_user()
            mock_get_sp.return_value = mock_sp
            resp = logged_in_client.post("/save_playlist", data={"track_ids": ""})
        # should redirect back to index with flash, not crash
        assert resp.status_code == 302

    def test_save_playlist_success(self, logged_in_client, mock_db):
        with patch("app.get_spotify_client") as mock_get_sp:
            mock_sp = MagicMock()
            mock_sp.current_user.return_value = fake_spotify_user()
            mock_sp._post.return_value = {"id": "playlist123"}
            mock_get_sp.return_value = mock_sp

            resp = logged_in_client.post(
                "/save_playlist",
                data={"track_ids": "spotify:track:1,spotify:track:2"},
            )
        assert resp.status_code == 302
        mock_sp.playlist_add_items.assert_called_once()
        mock_db.playlists.insert_one.assert_called_once()

    def test_save_playlist_handles_spotify_failure(self, logged_in_client):
        with patch("app.get_spotify_client") as mock_get_sp:
            mock_sp = MagicMock()
            mock_sp.current_user.return_value = fake_spotify_user()
            mock_sp._post.side_effect = Exception("Spotify API down")
            mock_get_sp.return_value = mock_sp
            resp = logged_in_client.post("/save_playlist",
                                          data={"track_ids": "spotify:track:1"})
        # should redirect, not crash
        assert resp.status_code == 302


# ── 404 handler ───────────────────────────────────────────────────────────────

class TestNotFound:
    def test_404_renders_template(self, client):
        resp = client.get("/this-page-does-not-exist-anywhere")
        assert resp.status_code == 404
        assert b"404" in resp.data or b"not found" in resp.data.lower()


# ── /history (full page) ──────────────────────────────────────────────────────

class TestHistoryPage:
    def test_history_redirects_when_not_logged_in(self, client):
        resp = client.get("/history")
        assert resp.status_code == 302
        assert "login" in resp.headers["Location"]

    def test_history_renders_for_logged_in_user(self, logged_in_client, mock_db):
        with patch("app.get_spotify_client") as mock_get_sp:
            mock_sp = MagicMock()
            mock_sp.current_user.return_value = fake_spotify_user()
            mock_get_sp.return_value = mock_sp
            mock_db.sessions.find.return_value.sort.return_value.limit.return_value = []

            resp = logged_in_client.get("/history")
        assert resp.status_code == 200
