from flask import (
    Blueprint, render_template, request, redirect, url_for,
    make_response, jsonify, flash
)
import requests as http_requests
from . import api_client

bp = Blueprint("main", __name__)

COOKIE = "vibe_token"


def _token():
    return request.cookies.get(COOKIE)


def _require_auth():
    """Return redirect to /login if no token, else None."""
    if not _token():
        return redirect(url_for("main.login"))
    return None


# ── Root ──────────────────────────────────────────────────────────────────────

@bp.route("/")
def index():
    if _token():
        return redirect(url_for("main.feed"))
    return redirect(url_for("main.login"))


# ── Auth ──────────────────────────────────────────────────────────────────────

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if _token():
            return redirect(url_for("main.feed"))
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    try:
        _, token = api_client.login(email, password)
        resp = make_response(redirect(url_for("main.feed")))
        resp.set_cookie(COOKIE, token, httponly=True, samesite="Lax")
        return resp
    except http_requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else 0
        error = "Wrong email or password." if status == 401 else "Something went wrong. Try again."
        return render_template("login.html", error=error), 400
    except Exception:
        return render_template("login.html", error="Could not reach the server."), 503


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        if _token():
            return redirect(url_for("main.feed"))
        return render_template("register.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    display_name = request.form.get("display_name", "").strip()
    age = request.form.get("age", "")
    city = request.form.get("city", "").strip()

    try:
        age_int = int(age)
    except ValueError:
        return render_template("register.html", error="Age must be a number.", form=request.form), 400

    try:
        _, token = api_client.register(email, password, display_name, age_int, city)
        resp = make_response(redirect(url_for("main.spotify_connect")))
        resp.set_cookie(COOKIE, token, httponly=True, samesite="Lax")
        return resp
    except http_requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else 0
        error = "An account with that email already exists." if status == 409 else "Registration failed. Try again."
        return render_template("register.html", error=error, form=request.form), 400
    except Exception:
        return render_template("register.html", error="Could not reach the server.", form=request.form), 503


@bp.route("/logout", methods=["POST"])
def logout():
    api_client.logout(_token())
    resp = make_response(redirect(url_for("main.login")))
    resp.delete_cookie(COOKIE)
    return resp


# ── Spotify connect ───────────────────────────────────────────────────────────

@bp.route("/spotify/connect")
def spotify_connect():
    guard = _require_auth()
    if guard:
        return guard
    url = api_client.get_spotify_connect_url(_token())
    return redirect(url)


@bp.route("/spotify/disconnect", methods=["POST"])
def spotify_disconnect():
    guard = _require_auth()
    if guard:
        return guard
    api_client.disconnect_spotify(_token())
    return redirect(url_for("main.settings"))


# ── Profile setup ─────────────────────────────────────────────────────────────

@bp.route("/profile/setup", methods=["GET", "POST"])
def profile_setup():
    guard = _require_auth()
    if guard:
        return guard

    if request.method == "POST":
        data = {
            k: v for k, v in {
                "bio": request.form.get("bio", "").strip() or None,
                "gender": request.form.get("gender", "").strip() or None,
                "gender_preference": request.form.get("gender_preference", "").strip() or None,
                "age_range_preference": {
                    "min": int(request.form.get("age_min", 18)),
                    "max": int(request.form.get("age_max", 99)),
                },
            }.items()
            if v is not None
        }
        try:
            api_client.update_profile(_token(), data)
            # Handle photo upload if provided
            if "photo" in request.files and request.files["photo"].filename:
                f = request.files["photo"]
                api_client.upload_photo(_token(), f.read(), f.content_type)
        except Exception:
            pass
        return redirect(url_for("main.feed"))

    try:
        user = api_client.get_me(_token())
    except Exception:
        user = {}
    return render_template("profile_setup.html", user=user)


# ── Feed ──────────────────────────────────────────────────────────────────────

@bp.route("/feed")
def feed():
    guard = _require_auth()
    if guard:
        return guard
    return render_template("feed.html")


# ── Profile detail ────────────────────────────────────────────────────────────

@bp.route("/profile/<user_id>")
def profile_detail(user_id):
    guard = _require_auth()
    if guard:
        return guard
    try:
        profile = api_client.get_profile(_token(), user_id)
    except http_requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return render_template("404.html"), 404
        profile = None
    except Exception:
        profile = None
    return render_template("profile_detail.html", profile=profile, user_id=user_id)


# ── Matches ───────────────────────────────────────────────────────────────────

@bp.route("/matches")
def matches():
    guard = _require_auth()
    if guard:
        return guard
    try:
        match_list = api_client.get_matches(_token())
    except Exception:
        match_list = []
    return render_template("matches.html", matches=match_list)


# ── Settings ──────────────────────────────────────────────────────────────────

@bp.route("/settings", methods=["GET", "POST"])
def settings():
    guard = _require_auth()
    if guard:
        return guard

    if request.method == "POST":
        data = {}
        for field in ("display_name", "city", "bio", "gender", "gender_preference"):
            val = request.form.get(field, "").strip()
            if val:
                data[field] = val
        age = request.form.get("age", "")
        if age.isdigit():
            data["age"] = int(age)
        age_min = request.form.get("age_min", "")
        age_max = request.form.get("age_max", "")
        if age_min.isdigit() and age_max.isdigit():
            data["age_range_preference"] = {"min": int(age_min), "max": int(age_max)}
        instagram = request.form.get("instagram", "").strip()
        phone = request.form.get("phone", "").strip()
        if instagram or phone:
            data["contact_info"] = {"instagram": instagram or None, "phone": phone or None}
        try:
            api_client.update_profile(_token(), data)
            if "photo" in request.files and request.files["photo"].filename:
                f = request.files["photo"]
                api_client.upload_photo(_token(), f.read(), f.content_type)
            success = "Profile updated."
        except Exception:
            success = None

        try:
            user = api_client.get_me(_token())
        except Exception:
            user = {}
        return render_template("settings.html", user=user, success=success)

    try:
        user = api_client.get_me(_token())
    except Exception:
        user = {}
    return render_template("settings.html", user=user)


# ── JSON API proxies (called by client-side JS) ────────────────────────────────

@bp.route("/api/feed")
def api_feed():
    guard = _require_auth()
    if guard:
        return jsonify({"error": "unauthorized"}), 401
    page = request.args.get("page", 0, type=int)
    try:
        data = api_client.get_feed(_token(), page)
        return jsonify(data)
    except http_requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else 500
        detail = e.response.json().get("detail", "error") if e.response is not None else "error"
        return jsonify({"error": detail}), status
    except Exception:
        return jsonify({"error": "server_error"}), 503


@bp.route("/api/likes/<user_id>", methods=["POST"])
def api_like(user_id):
    guard = _require_auth()
    if guard:
        return jsonify({"error": "unauthorized"}), 401
    try:
        data = api_client.like_user(_token(), user_id)
        return jsonify(data)
    except http_requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else 500
        return jsonify({"error": "error"}), status
    except Exception:
        return jsonify({"error": "server_error"}), 503


@bp.route("/api/matches/<match_id>/seen", methods=["PATCH"])
def api_match_seen(match_id):
    guard = _require_auth()
    if guard:
        return jsonify({"error": "unauthorized"}), 401
    try:
        api_client.mark_match_seen(_token(), match_id)
        return jsonify({"ok": True})
    except Exception:
        return jsonify({"error": "server_error"}), 503
