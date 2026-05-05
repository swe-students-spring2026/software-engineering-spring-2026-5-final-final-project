import requests
from . import config
from . import mock_data


def _url(path):
    return f"{config.BACKEND_URL}{path}"


def _cookies(token):
    return {"vibe_token": token} if token else {}


# ── Auth ──────────────────────────────────────────────────────────────────────

def login(email, password):
    if config.MOCK_MODE:
        return mock_data.MOCK_USER, "mock-token"
    resp = requests.post(_url("/api/auth/login"), json={"email": email, "password": password}, timeout=10)
    resp.raise_for_status()
    token = resp.cookies.get("vibe_token")
    return resp.json(), token


def register(email, password, display_name, age, city):
    if config.MOCK_MODE:
        return mock_data.MOCK_USER, "mock-token"
    resp = requests.post(
        _url("/api/auth/register"),
        json={"email": email, "password": password, "display_name": display_name, "age": age, "city": city},
        timeout=10,
    )
    resp.raise_for_status()
    token = resp.cookies.get("vibe_token")
    return resp.json(), token


def logout(token):
    if config.MOCK_MODE:
        return
    try:
        requests.post(_url("/api/auth/logout"), cookies=_cookies(token), timeout=10)
    except requests.RequestException:
        pass


def get_me(token):
    if config.MOCK_MODE:
        return mock_data.MOCK_USER
    resp = requests.get(_url("/api/auth/me"), cookies=_cookies(token), timeout=10)
    resp.raise_for_status()
    return resp.json()


# ── Users ─────────────────────────────────────────────────────────────────────

def get_profile(token, user_id):
    if config.MOCK_MODE:
        return mock_data.MOCK_PROFILE
    resp = requests.get(_url(f"/api/users/{user_id}"), cookies=_cookies(token), timeout=10)
    resp.raise_for_status()
    return resp.json()


def update_profile(token, data):
    if config.MOCK_MODE:
        return mock_data.MOCK_USER
    resp = requests.put(_url("/api/users/me"), json=data, cookies=_cookies(token), timeout=10)
    resp.raise_for_status()
    return resp.json()


def upload_photo(token, file_bytes, content_type):
    if config.MOCK_MODE:
        return mock_data.MOCK_USER
    resp = requests.post(
        _url("/api/users/me/photo"),
        files={"file": ("photo", file_bytes, content_type)},
        cookies=_cookies(token),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ── Spotify ───────────────────────────────────────────────────────────────────

def get_spotify_connect_url(token):
    if config.MOCK_MODE:
        return "/feed"
    resp = requests.get(_url("/api/spotify/connect"), cookies=_cookies(token), timeout=10, allow_redirects=False)
    return resp.headers.get("Location", "/feed")


def disconnect_spotify(token):
    if config.MOCK_MODE:
        return
    requests.post(_url("/api/spotify/disconnect"), cookies=_cookies(token), timeout=10)


# ── Feed ──────────────────────────────────────────────────────────────────────

def get_feed(token, page=0):
    if config.MOCK_MODE:
        return mock_data.MOCK_FEED
    resp = requests.get(_url(f"/api/feed?page={page}"), cookies=_cookies(token), timeout=10)
    resp.raise_for_status()
    return resp.json()


# ── Likes ─────────────────────────────────────────────────────────────────────

def like_user(token, user_id):
    if config.MOCK_MODE:
        return {"matched": False, "match_id": None}
    resp = requests.post(_url(f"/api/likes/{user_id}"), cookies=_cookies(token), timeout=10)
    resp.raise_for_status()
    return resp.json()


def unlike_user(token, user_id):
    if config.MOCK_MODE:
        return
    requests.delete(_url(f"/api/likes/{user_id}"), cookies=_cookies(token), timeout=10)


# ── Matches ───────────────────────────────────────────────────────────────────

def get_matches(token):
    if config.MOCK_MODE:
        return mock_data.MOCK_MATCHES
    resp = requests.get(_url("/api/matches"), cookies=_cookies(token), timeout=10)
    resp.raise_for_status()
    return resp.json()


def mark_match_seen(token, match_id):
    if config.MOCK_MODE:
        return
    requests.patch(_url(f"/api/matches/{match_id}/seen"), cookies=_cookies(token), timeout=10)
