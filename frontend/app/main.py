import os
import secrets
from functools import wraps

import requests
from authlib.integrations.flask_client import OAuth
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

API_URL = os.environ.get("API_URL", "http://backend:8000")
API_INTERNAL_TOKEN = os.environ.get("API_INTERNAL_TOKEN", "")
FRONTEND_PUBLIC_URL = os.environ.get("FRONTEND_PUBLIC_URL", "http://localhost:3000").rstrip("/")

oauth = OAuth(app)
google = oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# Default timeouts (seconds) for API proxy calls
_T_SHORT = 10   # auth, profile, schools, simple lookups
_T_NORMAL = 30  # class search, professor lookups
_T_LONG = 90    # chat (Gemini tool-calling loop), transcript upload, bulletin reload


def _api_headers() -> dict[str, str]:
    return {"X-Internal-API-Token": API_INTERNAL_TOKEN} if API_INTERNAL_TOKEN else {}


def _request_api(method, path: str, *, timeout: int, **kwargs):
    headers = {**_api_headers(), **kwargs.pop("headers", {})}
    try:
        return method(f"{API_URL}{path}", headers=headers, timeout=timeout, **kwargs)
    except Exception:
        return None


def _response_json(resp) -> dict | list:
    try:
        return resp.json()
    except ValueError:
        return {"error": "Backend returned a non-JSON response."}


def _proxy_response(resp):
    if resp is None:
        return jsonify({"error": "Could not reach the backend API."}), 502
    return jsonify(_response_json(resp)), resp.status_code


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def _get_user_profile(email: str) -> dict:
    resp = _request_api(requests.get, "/user/profile", params={"email": email}, timeout=_T_SHORT)
    if resp is not None and resp.status_code == 200:
        payload = _response_json(resp)
        if isinstance(payload, dict):
            return payload
    return {}


def _google_redirect_uri() -> str:
    return f"{FRONTEND_PUBLIC_URL}{url_for('auth_google_callback')}"


def _is_blank_chat_value(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set)):
        return len(value) == 0
    return False


def _merge_chat_context(payload: dict, profile: dict) -> dict:
    merged = dict(payload)

    profile_context = {
        "name": profile.get("name", ""),
        "school": profile.get("school", ""),
        "major": profile.get("major", ""),
        "minor": profile.get("minor", ""),
        "graduation_year": profile.get("graduation_year", ""),
        "completed_courses": profile.get("completed_courses", []),
        "current_courses": profile.get("current_courses", []),
    }

    for key, profile_value in profile_context.items():
        if _is_blank_chat_value(merged.get(key)):
            merged[key] = profile_value

    merged["student_profile"] = {
        key: merged.get(key)
        for key in profile_context
        if not _is_blank_chat_value(merged.get(key))
    }
    return merged


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.get("/login")
def login():
    if session.get("user"):
        return redirect(url_for("index"))
    return render_template("login.html")


@app.post("/login")
def login_post():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email.endswith("@nyu.edu"):
        return render_template("login.html", error="Only @nyu.edu email addresses are allowed.")

    resp = _request_api(
        requests.post,
        "/auth/login",
        json={"email": email, "password": password},
        timeout=_T_SHORT,
    )
    if resp is None:
        error = "Could not reach the server. Please try again."
    elif resp.status_code == 200:
        data = _response_json(resp)
        session["user"] = {"email": email, "name": data.get("name", email) if isinstance(data, dict) else email}
        return redirect(url_for("index"))
    else:
        data = _response_json(resp)
        error = data.get("error", "Invalid email or password.") if isinstance(data, dict) else "Invalid email or password."

    return render_template("login.html", error=error)


@app.post("/register")
def register_post():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    name = request.form.get("name", "").strip()

    if not email.endswith("@nyu.edu"):
        return render_template("login.html", tab="register", error="Only @nyu.edu email addresses are allowed.")

    resp = _request_api(
        requests.post,
        "/auth/register",
        json={"email": email, "password": password, "name": name},
        timeout=_T_SHORT,
    )
    if resp is None:
        error = "Could not reach the server. Please try again."
    elif resp.status_code == 201:
        session["user"] = {"email": email, "name": name or email}
        return redirect(url_for("index"))
    else:
        data = _response_json(resp)
        error = data.get("error", "Registration failed.") if isinstance(data, dict) else "Registration failed."

    return render_template("login.html", tab="register", error=error)


@app.get("/auth/google")
def auth_google():
    return google.authorize_redirect(
        _google_redirect_uri(),
        prompt="select_account",
    )


@app.get("/auth/google/callback")
def auth_google_callback():
    try:
        token = google.authorize_access_token()
        userinfo = token.get("userinfo") or {}
        email = userinfo.get("email", "").lower()

        if not email.endswith("@nyu.edu"):
            return render_template("login.html", error="Only @nyu.edu Google accounts are allowed.")

        name = userinfo.get("name", email)
        resp = _request_api(
            requests.post,
            "/auth/google",
            json={"email": email, "name": name},
            timeout=_T_SHORT,
        )
        if resp is None or resp.status_code >= 400:
            return render_template("login.html", error="Could not finish Google sign-in.")

        session["user"] = {"email": email, "name": name}
    except Exception as exc:
        return render_template("login.html", error=f"Google sign-in failed: {exc}")

    return redirect(url_for("index"))


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Page routes (protected) ───────────────────────────────────────────────────

@app.get("/")
@login_required
def index():
    return render_template("index.html", user=session["user"])


@app.get("/schedule")
@login_required
def schedule():
    return render_template("schedule.html", user=session["user"])


@app.get("/programs")
@login_required
def programs_page():
    return render_template("programs.html", user=session["user"])


@app.get("/profile")
@login_required
def profile_page():
    email = session["user"]["email"]
    profile = _get_user_profile(email)
    return render_template("profile.html", user=session["user"], profile=profile)


@app.get("/graduation")
@login_required
def graduation_page():
    email = session["user"]["email"]
    profile = _get_user_profile(email)
    return render_template("graduation.html", user=session["user"], profile=profile)


@app.get("/professor")
@login_required
def professor_page():
    return render_template(
        "professor.html",
        user=session["user"],
        professor_name=request.args.get("name", "").strip(),
    )


# ── API proxy routes ──────────────────────────────────────────────────────────

@app.get("/api/programs")
@login_required
def programs():
    resp = _request_api(requests.get, "/programs", timeout=_T_SHORT)
    if resp is None:
        return jsonify({"error": "Could not reach the backend API."}), 502
    response = jsonify(_response_json(resp))
    response.status_code = resp.status_code
    # Propagate Cache-Control from the API so browsers/CDNs can cache the static list
    cache_control = resp.headers.get("Cache-Control") if hasattr(resp, "headers") else None
    if isinstance(cache_control, str):
        response.headers["Cache-Control"] = cache_control
    return response


@app.get("/api/program-requirements")
@login_required
def program_requirements():
    resp = _request_api(requests.get, "/program-requirements", params=dict(request.args), timeout=_T_NORMAL)
    return _proxy_response(resp)


@app.get("/api/classes")
@login_required
def proxy_classes():
    params = dict(request.args)
    resp = _request_api(requests.get, "/classes", params=params, timeout=_T_NORMAL)
    return _proxy_response(resp)


@app.post("/api/classes/reload")
@login_required
def proxy_reload_class():
    payload = request.get_json(silent=True) or {}
    resp = _request_api(requests.post, "/classes/reload", json=payload, timeout=_T_LONG)
    return _proxy_response(resp)


@app.get("/api/schools")
@login_required
def proxy_schools():
    resp = _request_api(requests.get, "/classes/schools", timeout=_T_SHORT)
    return _proxy_response(resp)


@app.get("/api/campuses")
@login_required
def proxy_campuses():
    resp = _request_api(requests.get, "/classes/campuses", timeout=_T_SHORT)
    return _proxy_response(resp)


@app.get("/api/professors")
@login_required
def proxy_professors():
    resp = _request_api(requests.get, "/professors", params=dict(request.args), timeout=_T_NORMAL)
    return _proxy_response(resp)


@app.get("/api/professors/profile")
@login_required
def proxy_professor_profile():
    resp = _request_api(requests.get, "/professors/profile", params=dict(request.args), timeout=_T_NORMAL)
    return _proxy_response(resp)


@app.get("/api/profile")
@login_required
def proxy_get_profile():
    email = session["user"]["email"]
    resp = _request_api(requests.get, "/user/profile", params={"email": email}, timeout=_T_SHORT)
    return _proxy_response(resp)


@app.put("/api/profile")
@login_required
def proxy_update_profile():
    data = request.get_json(silent=True) or {}
    data["email"] = session["user"]["email"]
    resp = _request_api(requests.put, "/user/profile", json=data, timeout=_T_SHORT)
    if resp is not None and resp.status_code == 200:
        if "name" in data:
            session["user"] = {**session["user"], "name": data["name"]}
    return _proxy_response(resp)


@app.post("/api/transcript")
@login_required
def proxy_transcript():
    file = request.files.get("transcript")
    if not file:
        return jsonify({"error": "no file uploaded"}), 400
    email = session["user"]["email"]
    resp = _request_api(
        requests.post,
        "/user/transcript",
        data={"email": email},
        files={"transcript": (file.filename, file.stream, file.mimetype)},
        timeout=_T_LONG,
    )
    return _proxy_response(resp)


@app.post("/api/chat")
@login_required
def proxy_chat():
    payload = request.get_json(silent=True) or {}
    profile = _get_user_profile(session["user"]["email"])
    payload = _merge_chat_context(payload, profile)
    resp = _request_api(requests.post, "/chat", json=payload, timeout=_T_LONG)
    return _proxy_response(resp)


if __name__ == "__main__":
    port = int(os.environ.get("PORT") or os.environ.get("FRONTEND_INTERNAL_PORT", "3000"))
    app.run(host="0.0.0.0", port=port)
