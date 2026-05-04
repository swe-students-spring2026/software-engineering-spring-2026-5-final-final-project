import pytest
from unittest.mock import patch, MagicMock
import requests as http_requests

from app.main import create_app


@pytest.fixture
def app():
    application = create_app()
    application.config["TESTING"] = True
    application.config["WTF_CSRF_ENABLED"] = False
    return application


@pytest.fixture
def client(app):
    return app.test_client()


TOKEN = "test-token"


@pytest.fixture
def ac(app):
    """Authenticated test client — cookie pre-set."""
    c = app.test_client()
    c.set_cookie("vibe_token", TOKEN)
    return c

MOCK_USER = {
    "user_id": "u1",
    "email": "a@b.com",
    "display_name": "Test",
    "age": 23,
    "city": "New York",
    "bio": "hi",
    "gender": "non-binary",
    "gender_preference": None,
    "age_range_preference": {"min": 18, "max": 30},
    "photo_url": None,
    "contact_info": {"phone": None, "instagram": None},
    "is_spotify_connected": True,
    "spotify": {
        "top_genres": ["indie rock"],
        "top_artists": [{"name": "Big Thief"}],
        "audio_features": {"energy": 0.5, "valence": 0.5, "danceability": 0.5, "tempo": 120},
        "last_synced": "2026-05-01T00:00:00",
    },
}

MOCK_FEED = {
    "profiles": [
        {
            "user_id": "u2",
            "display_name": "Jordan",
            "age": 24,
            "city": "New York",
            "bio": "hi",
            "top_genres": ["folk"],
            "top_artists": [{"name": "Phoebe Bridgers"}],
            "match_score": 0.8,
            "photo_url": None,
        }
    ],
    "page": 0,
    "has_more": False,
}

MOCK_MATCHES = [
    {
        "match_id": "m1",
        "user_id": "u2",
        "display_name": "Jordan",
        "age": 24,
        "city": "New York",
        "bio": "hi",
        "top_genres": ["folk"],
        "top_artists": [{"name": "Phoebe Bridgers"}],
        "photo_url": None,
        "contact_info": {"phone": None, "instagram": "jj"},
        "is_new": True,
        "matched_at": "2026-05-01T00:00:00",
    }
]

MOCK_PROFILE = {
    "user_id": "u2",
    "display_name": "Jordan",
    "age": 24,
    "city": "New York",
    "bio": "hi",
    "top_genres": ["folk"],
    "top_artists": [{"name": "Phoebe Bridgers"}],
    "photo_url": None,
    "contact_info": {"phone": None, "instagram": "jj"},
}


# ── Root ──────────────────────────────────────────────────────────────────────

def test_root_no_cookie_redirects_login(client):
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_root_with_cookie_redirects_feed(client):
    resp = client.get("/", **auth())
    assert resp.status_code == 302
    assert "/feed" in resp.headers["Location"]


# ── Login ─────────────────────────────────────────────────────────────────────

def test_login_get(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"vibe" in resp.data


def test_login_get_with_cookie_redirects(client):
    resp = client.get("/login", **auth())
    assert resp.status_code == 302
    assert "/feed" in resp.headers["Location"]


def test_login_post_success(client):
    with patch("app.routes.api_client.login", return_value=(MOCK_USER, TOKEN)):
        resp = client.post("/login", data={"email": "a@b.com", "password": "pass"})
    assert resp.status_code == 302
    assert "/feed" in resp.headers["Location"]
    assert "vibe_token" in resp.headers.get("Set-Cookie", "")


def test_login_post_wrong_password(client):
    err = http_requests.HTTPError(response=MagicMock(status_code=401))
    with patch("app.routes.api_client.login", side_effect=err):
        resp = client.post("/login", data={"email": "a@b.com", "password": "wrong"})
    assert resp.status_code == 400
    assert b"Wrong email" in resp.data


def test_login_post_server_error(client):
    with patch("app.routes.api_client.login", side_effect=Exception("down")):
        resp = client.post("/login", data={"email": "a@b.com", "password": "pass"})
    assert resp.status_code == 503


def test_login_post_other_http_error(client):
    err = http_requests.HTTPError(response=MagicMock(status_code=500))
    with patch("app.routes.api_client.login", side_effect=err):
        resp = client.post("/login", data={"email": "a@b.com", "password": "pass"})
    assert resp.status_code == 400
    assert b"Something went wrong" in resp.data


# ── Register ──────────────────────────────────────────────────────────────────

def test_register_get(client):
    resp = client.get("/register")
    assert resp.status_code == 200
    assert b"Create" in resp.data


def test_register_get_with_cookie_redirects(client):
    resp = client.get("/register", **auth())
    assert resp.status_code == 302


def test_register_post_success(client):
    with patch("app.routes.api_client.register", return_value=(MOCK_USER, TOKEN)):
        resp = client.post("/register", data={
            "email": "a@b.com", "password": "password1",
            "display_name": "Test", "age": "23", "city": "New York",
        })
    assert resp.status_code == 302
    assert "vibe_token" in resp.headers.get("Set-Cookie", "")


def test_register_post_bad_age(client):
    resp = client.post("/register", data={
        "email": "a@b.com", "password": "password1",
        "display_name": "Test", "age": "notanumber", "city": "New York",
    })
    assert resp.status_code == 400
    assert b"Age must be a number" in resp.data


def test_register_post_conflict(client):
    err = http_requests.HTTPError(response=MagicMock(status_code=409))
    with patch("app.routes.api_client.register", side_effect=err):
        resp = client.post("/register", data={
            "email": "a@b.com", "password": "password1",
            "display_name": "Test", "age": "23", "city": "New York",
        })
    assert resp.status_code == 400
    assert b"already exists" in resp.data


def test_register_post_server_error(client):
    with patch("app.routes.api_client.register", side_effect=Exception("down")):
        resp = client.post("/register", data={
            "email": "a@b.com", "password": "password1",
            "display_name": "Test", "age": "23", "city": "New York",
        })
    assert resp.status_code == 503


def test_register_post_other_http_error(client):
    err = http_requests.HTTPError(response=MagicMock(status_code=500))
    with patch("app.routes.api_client.register", side_effect=err):
        resp = client.post("/register", data={
            "email": "a@b.com", "password": "password1",
            "display_name": "Test", "age": "23", "city": "New York",
        })
    assert resp.status_code == 400
    assert b"Registration failed" in resp.data


# ── Logout ────────────────────────────────────────────────────────────────────

def test_logout(client):
    with patch("app.routes.api_client.logout"):
        resp = client.post("/logout", **auth())
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


# ── Spotify connect ───────────────────────────────────────────────────────────

def test_spotify_connect_no_auth(client):
    resp = client.get("/spotify/connect")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_spotify_connect_redirects(client):
    with patch("app.routes.api_client.get_spotify_connect_url", return_value="https://accounts.spotify.com/auth"):
        resp = client.get("/spotify/connect", **auth())
    assert resp.status_code == 302


def test_spotify_disconnect_no_auth(client):
    resp = client.post("/spotify/disconnect")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_spotify_disconnect(client):
    with patch("app.routes.api_client.disconnect_spotify"):
        resp = client.post("/spotify/disconnect", **auth())
    assert resp.status_code == 302
    assert "/settings" in resp.headers["Location"]


# ── Profile setup ─────────────────────────────────────────────────────────────

def test_profile_setup_no_auth(client):
    resp = client.get("/profile/setup")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_profile_setup_get(client):
    with patch("app.routes.api_client.get_me", return_value=MOCK_USER):
        resp = client.get("/profile/setup", **auth())
    assert resp.status_code == 200


def test_profile_setup_get_error(client):
    with patch("app.routes.api_client.get_me", side_effect=Exception("err")):
        resp = client.get("/profile/setup", **auth())
    assert resp.status_code == 200


def test_profile_setup_post(client):
    with patch("app.routes.api_client.update_profile", return_value=MOCK_USER):
        resp = client.post(
            "/profile/setup",
            data={"bio": "hi", "gender": "non-binary", "gender_preference": "", "age_min": "18", "age_max": "30"},
            **auth(),
        )
    assert resp.status_code == 302
    assert "/feed" in resp.headers["Location"]


def test_profile_setup_post_exception(client):
    with patch("app.routes.api_client.update_profile", side_effect=Exception("err")):
        resp = client.post(
            "/profile/setup",
            data={"bio": "hi", "age_min": "18", "age_max": "30"},
            **auth(),
        )
    assert resp.status_code == 302


# ── Feed ──────────────────────────────────────────────────────────────────────

def test_feed_no_auth(client):
    resp = client.get("/feed")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_feed_with_auth(client):
    resp = client.get("/feed", **auth())
    assert resp.status_code == 200
    assert b"vibe" in resp.data


# ── API feed proxy ────────────────────────────────────────────────────────────

def test_api_feed_no_auth(client):
    resp = client.get("/api/feed")
    assert resp.status_code == 401


def test_api_feed_success(client):
    with patch("app.routes.api_client.get_feed", return_value=MOCK_FEED):
        resp = client.get("/api/feed", **auth())
    assert resp.status_code == 200
    data = resp.get_json()
    assert "profiles" in data


def test_api_feed_http_error(client):
    mock_resp = MagicMock(status_code=403)
    mock_resp.json.return_value = {"detail": "spotify_required"}
    err = http_requests.HTTPError(response=mock_resp)
    with patch("app.routes.api_client.get_feed", side_effect=err):
        resp = client.get("/api/feed", **auth())
    assert resp.status_code == 403


def test_api_feed_exception(client):
    with patch("app.routes.api_client.get_feed", side_effect=Exception("down")):
        resp = client.get("/api/feed", **auth())
    assert resp.status_code == 503


# ── API like proxy ────────────────────────────────────────────────────────────

def test_api_like_no_auth(client):
    resp = client.post("/api/likes/u2")
    assert resp.status_code == 401


def test_api_like_success(client):
    with patch("app.routes.api_client.like_user", return_value={"matched": False, "match_id": None}):
        resp = client.post("/api/likes/u2", **auth())
    assert resp.status_code == 200
    assert resp.get_json()["matched"] is False


def test_api_like_matched(client):
    with patch("app.routes.api_client.like_user", return_value={"matched": True, "match_id": "m1"}):
        resp = client.post("/api/likes/u2", **auth())
    assert resp.status_code == 200
    assert resp.get_json()["matched"] is True


def test_api_like_http_error(client):
    err = http_requests.HTTPError(response=MagicMock(status_code=429))
    with patch("app.routes.api_client.like_user", side_effect=err):
        resp = client.post("/api/likes/u2", **auth())
    assert resp.status_code == 429


def test_api_like_exception(client):
    with patch("app.routes.api_client.like_user", side_effect=Exception("down")):
        resp = client.post("/api/likes/u2", **auth())
    assert resp.status_code == 503


# ── API matches seen ──────────────────────────────────────────────────────────

def test_api_match_seen_no_auth(client):
    resp = client.patch("/api/matches/m1/seen")
    assert resp.status_code == 401


def test_api_match_seen_success(client):
    with patch("app.routes.api_client.mark_match_seen"):
        resp = client.patch("/api/matches/m1/seen", **auth())
    assert resp.status_code == 200


def test_api_match_seen_exception(client):
    with patch("app.routes.api_client.mark_match_seen", side_effect=Exception("err")):
        resp = client.patch("/api/matches/m1/seen", **auth())
    assert resp.status_code == 503


# ── Profile detail ────────────────────────────────────────────────────────────

def test_profile_detail_no_auth(client):
    resp = client.get("/profile/u2")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_profile_detail_found(client):
    with patch("app.routes.api_client.get_profile", return_value=MOCK_PROFILE):
        resp = client.get("/profile/u2", **auth())
    assert resp.status_code == 200
    assert b"Jordan" in resp.data


def test_profile_detail_not_found(client):
    err = http_requests.HTTPError(response=MagicMock(status_code=404))
    with patch("app.routes.api_client.get_profile", side_effect=err):
        resp = client.get("/profile/u2", **auth())
    assert resp.status_code == 404


def test_profile_detail_http_error_other(client):
    err = http_requests.HTTPError(response=MagicMock(status_code=500))
    with patch("app.routes.api_client.get_profile", side_effect=err):
        resp = client.get("/profile/u2", **auth())
    assert resp.status_code == 200  # renders with profile=None


def test_profile_detail_exception(client):
    with patch("app.routes.api_client.get_profile", side_effect=Exception("err")):
        resp = client.get("/profile/u2", **auth())
    assert resp.status_code == 200


# ── Matches ───────────────────────────────────────────────────────────────────

def test_matches_no_auth(client):
    resp = client.get("/matches")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_matches_with_data(client):
    with patch("app.routes.api_client.get_matches", return_value=MOCK_MATCHES):
        resp = client.get("/matches", **auth())
    assert resp.status_code == 200
    assert b"Jordan" in resp.data


def test_matches_empty(client):
    with patch("app.routes.api_client.get_matches", return_value=[]):
        resp = client.get("/matches", **auth())
    assert resp.status_code == 200
    assert b"No matches" in resp.data


def test_matches_exception(client):
    with patch("app.routes.api_client.get_matches", side_effect=Exception("err")):
        resp = client.get("/matches", **auth())
    assert resp.status_code == 200


# ── Settings ──────────────────────────────────────────────────────────────────

def test_settings_no_auth(client):
    resp = client.get("/settings")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_settings_get(client):
    with patch("app.routes.api_client.get_me", return_value=MOCK_USER):
        resp = client.get("/settings", **auth())
    assert resp.status_code == 200
    assert b"Profile" in resp.data


def test_settings_get_exception(client):
    with patch("app.routes.api_client.get_me", side_effect=Exception("err")):
        resp = client.get("/settings", **auth())
    assert resp.status_code == 200


def test_settings_post_success(client):
    with patch("app.routes.api_client.update_profile", return_value=MOCK_USER), \
         patch("app.routes.api_client.get_me", return_value=MOCK_USER):
        resp = client.post(
            "/settings",
            data={
                "display_name": "New Name", "city": "Brooklyn", "bio": "hi",
                "age": "24", "gender": "non-binary", "gender_preference": "",
                "age_min": "20", "age_max": "30",
                "instagram": "mynew", "phone": "",
            },
            **auth(),
        )
    assert resp.status_code == 200
    assert b"updated" in resp.data


def test_settings_post_exception(client):
    with patch("app.routes.api_client.update_profile", side_effect=Exception("err")), \
         patch("app.routes.api_client.get_me", return_value=MOCK_USER):
        resp = client.post(
            "/settings",
            data={"display_name": "X", "city": "NYC", "bio": "", "age": "", "gender": "",
                  "gender_preference": "", "age_min": "", "age_max": "", "instagram": "", "phone": ""},
            **auth(),
        )
    assert resp.status_code == 200


def test_settings_post_no_success(client):
    """POST with no contact info or age range should still save display_name."""
    with patch("app.routes.api_client.update_profile", return_value=MOCK_USER), \
         patch("app.routes.api_client.get_me", return_value=MOCK_USER):
        resp = client.post(
            "/settings",
            data={"display_name": "X", "city": "", "bio": "", "age": "notnum",
                  "gender": "", "gender_preference": "", "age_min": "bad", "age_max": "bad",
                  "instagram": "", "phone": ""},
            **auth(),
        )
    assert resp.status_code == 200
