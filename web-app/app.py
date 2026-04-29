# main entry point for the web app
import datetime
import os
import requests
import pymongo
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from cities import CITIES

load_dotenv()
app = Flask(__name__)
# set the secret key for session management
app.secret_key = os.getenv("SECRET_KEY")
# connect to MongoDB
client = pymongo.MongoClient(os.getenv("MONGO_URI", "mongodb://mongo:27017"))
db = client[os.getenv("MONGO_DB_NAME", "moodmusic")]

ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://ml-service:8000")


def get_sp_oauth():
    return SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scope="user-read-private user-read-email playlist-modify-public playlist-modify-private",
        cache_handler=spotipy.cache_handler.MemoryCacheHandler(),
    )


def get_spotify_client():
    """Return a logged-in Spotipy client, refreshing tokens as needed."""
    token_info = session.get("token_info")
    if not token_info:
        return None
    if get_sp_oauth().is_token_expired(token_info):
        token_info = get_sp_oauth().refresh_access_token(token_info["refresh_token"])
        session["token_info"] = token_info
    return spotipy.Spotify(auth=token_info["access_token"])


def get_recent_history(user_id, limit=5):
    if not user_id:
        return []
    cursor = db.sessions.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    return list(cursor)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    sp = get_spotify_client()
    if not sp:
        return redirect(url_for("login"))

    user_info = sp.current_user()
    user_id = session.get("user_id")

    return render_template(
        "index.html",
        username=user_info.get("display_name") or user_id,
        history=get_recent_history(user_id),
        cities=CITIES,
    )


@app.route("/login")
def login():
    if session.get("token_info"):
        return redirect(url_for("index"))
    auth_url = get_sp_oauth().get_authorize_url()
    return render_template("login.html", auth_url=auth_url)


@app.route("/callback")
def callback():
    code = request.args.get("code")
    try:
        token_info = get_sp_oauth().get_access_token(code)
    except Exception as e:  # spotipy raises broad exceptions
        return render_template("login.html", error=f"Spotify authentication failed: {e}"), 400

    sp = spotipy.Spotify(auth=token_info["access_token"])
    user_info = sp.current_user()
    session["user_id"] = user_info["id"]
    session["token_info"] = token_info
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/recommend", methods=["POST"])
def recommend():
    sp = get_spotify_client()
    if not sp:
        return redirect(url_for("login"))

    mood = request.form.get("mood_text", "").strip()
    mood_label = request.form.get("mood_label", "").strip()
    energy = request.form.get("energy", "50")
    valence = request.form.get("valence", "50")
    city_lat = request.form.get("city_lat", "40.7128")
    city_lon = request.form.get("city_lon", "-74.0060")
    city_name = request.form.get("city_name", "New York, NY")

    user_info = sp.current_user()
    user_id = session.get("user_id")
    username = user_info.get("display_name") or user_id

    # weather
    weather = {}
    weather_desc = "—"
    try:
        weather_resp = requests.get(
            f"{ML_SERVICE_URL}/weather",
            params={"lat": city_lat, "lon": city_lon},
            timeout=10,
        )
        weather_resp.raise_for_status()
        weather = weather_resp.json()
        temp_f = round(weather.get("temp", 0) * 9 / 5 + 32)
        weather_desc = f"{temp_f}°F · {weather.get('condition', '—')}"
    except requests.RequestException as e:
        flash(f"Weather fetch failed: {e}", "error")
        return render_template(
            "index.html",
            username=username,
            cities=CITIES,
            mood_text=mood,
            mood_label=mood_label,
            energy=energy,
            valence=valence,
            city_lat=city_lat,
            city_lon=city_lon,
            city_name=city_name,
            history=get_recent_history(user_id),
        )

    # ml prediction
    try:
        predict_resp = requests.post(
            f"{ML_SERVICE_URL}/predict",
            json={
                "mood": mood or mood_label or "neutral",
                "weather": weather,
                "user_id": user_id,
                "limit": 10,
            },
            timeout=100,
        )
        predict_resp.raise_for_status()
        result = predict_resp.json()
    except requests.RequestException as e:
        flash(f"ML service error: {e}", "error")
        return render_template(
            "index.html",
            username=username,
            cities=CITIES,
            mood_text=mood,
            mood_label=mood_label,
            energy=energy,
            valence=valence,
            weather_desc=weather_desc,
            city_lat=city_lat,
            city_lon=city_lon,
            city_name=city_name,
            history=get_recent_history(user_id),
        )

    tracks = result.get("tracks", [])
    track_ids = [t.get("uri") or t.get("id") for t in tracks if t.get("uri") or t.get("id")]

    return render_template(
        "index.html",
        username=username,
        tracks=tracks,
        session_id=result.get("session_id"),
        history=get_recent_history(user_id),
        track_ids=track_ids,
        cities=CITIES,
        weather_desc=weather_desc,
        city_name=city_name,
        city_lat=city_lat,
        city_lon=city_lon,
        mood_text=mood,
        mood_label=mood_label,
        energy=energy,
        valence=valence,
    )


@app.route("/save_playlist", methods=["POST"])
def save_playlist():
    track_ids = request.form.get("track_ids", "")
    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("login"))
    
    sp = get_spotify_client()
    if not sp:
        flash("Spotify authentication required to save playlist.", "error")
        return redirect(url_for("login"))
    
    if track_ids:
        playlist_name = f"Moodify: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        try:
            user_id = sp.current_user()["id"]
            
            playlist = sp._post("me/playlists", payload={
                "name": f"Moodify: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "public": False,
                "description": "Playlist generated by Moodify based on your mood and weather."
            })

            items = [t for t in track_ids.split(",") if t.strip()]
            if items:
                sp.playlist_add_items(playlist["id"], items)
        
            db.playlists.insert_one({
                "user_id": user_id,
                "tracks": track_ids.split(","),
                "created_at": datetime.datetime.now(datetime.timezone.utc),
            })
            
            flash("Playlist saved!", "success")
        except Exception as e:
    
            flash(f"Failed to save playlist: {e}", "error")
    else:
        flash("No tracks to save.", "error")

    return redirect(url_for("index"))


@app.route("/history")
def history_page():
    sp = get_spotify_client()
    if not sp:
        return redirect(url_for("login"))

    user_info = sp.current_user()
    user_id = session.get("user_id")
    return render_template(
        "history.html",
        username=user_info.get("display_name") or user_id,
        history=get_recent_history(user_id, limit=50),
    )


@app.errorhandler(404)
def page_not_found(_):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
