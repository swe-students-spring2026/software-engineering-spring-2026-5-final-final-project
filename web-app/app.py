# main entry point for the web app
import datetime
import os
import re
import requests  
import pymongo
from bson.objectid import ObjectId
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for, session
from datetime import timedelta
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from cities import CITIES

# create the Flask app
app = Flask(__name__)
# load environment variables from .env file
load_dotenv()
# set the secret key for session management
app.secret_key = os.getenv("SECRET_KEY")
# connect to MongoDB
client = pymongo.MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
db = client[os.getenv("MONGO_DB_NAME", "moodmusic")]
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://ml-service:8000")

# set up Spotify API credentials
sp_oauth = SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
    scope="user-read-private user-read-email playlist-modify-public playlist-modify-private",
)

# helper function to get Spotify client with valid access token
def get_spotify_client():
    token_info = session.get("token_info")
    if not token_info:
        return None
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        session["token_info"] = token_info
    return spotipy.Spotify(auth=token_info["access_token"])

# index route
@app.route("/")
def index():
    # check if user is logged in by looking for token info in session
    sp = get_spotify_client()
    if not sp:
        return redirect(url_for("login"))
    
    user_info = sp.current_user()
    
    history = []
    user_id = session.get("user_id")
    if user_id:
        history_cursor = db.sessions.find({"user_id": user_id}).sort("created_at", -1).limit(5)
        history = list(history_cursor)
    
    return render_template("index.html",
        username=user_info["display_name"],
        user_image=user_info["images"][0]["url"] if user_info["images"] else None,
        history=history,
        cities=CITIES,
    )


@app.route("/login")
def login():
    # check if user is already logged in
    if session.get("token_info"):
        return redirect(url_for("index"))
    
    auth_url = sp_oauth.get_authorize_url()
    return render_template("login.html", auth_url=auth_url)

# callback route for Spotify authentication
@app.route("/callback")
def callback():
    code = request.args.get("code")
    token_info = sp_oauth.get_access_token(code)
    access_token = token_info["access_token"]
    sp = spotipy.Spotify(auth=access_token)
    user_info = sp.current_user()
    user_id = user_info["id"]
    # store user info in session
    session["user_id"] = user_id
    session["token_info"] = token_info
    session["access_token"] = access_token
    return redirect(url_for("index"))

# logout route
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))



@app.route("/recommend", methods=["POST"])
def recommend():
    sp = get_spotify_client()
    if not sp:
        return redirect(url_for("login"))

    mood = request.form.get("mood_text", "")
    city_lat  = request.form.get("city_lat",  "40.7128")
    city_lon  = request.form.get("city_lon",  "-74.0060")
    city_name = request.form.get("city_name", "New York, NY")

    # Fetch weather from the ML service using coordinates
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
        return render_template("index.html", error=f"Weather fetch failed: {e}", cities=CITIES)

    # Call the ML prediction endpoint
    try:
        predict_resp = requests.post(
            f"{ML_SERVICE_URL}/predict",
            json={
                "mood": mood,
                "weather": weather,
                "user_id": session.get("user_id"),
                "limit": 10,
            },
            timeout=30,
        )
        predict_resp.raise_for_status()
        result = predict_resp.json()
        print("ML result:", result)  # ← add this
        print("Tracks:", result.get("tracks"))
    except requests.RequestException as e:
        return render_template("index.html", error=f"ML service error: {e}", cities=CITIES)

    history = []
    user_id = session.get("user_id")
    if user_id:
        history_cursor = db.sessions.find({"user_id": user_id}).sort("created_at", -1).limit(5)
        history = list(history_cursor)

    # Use display name if possible, fallback to user_id
    user_info = sp.current_user()
    username = user_info.get("display_name", user_id)

    return render_template(
        "index.html",
        username=username,
        tracks=result.get("tracks", []),
        session_id=result.get("session_id"),
        history=history,
        track_ids=[t.get("id") for t in result.get("tracks", []) if t.get("id")],
        cities=CITIES,
        weather_desc=weather_desc,
        city_name=city_name,
        city_lat=city_lat,
        city_lon=city_lon,
    )

@app.route("/save_playlist", methods=["POST"])
def save_playlist():
    track_ids = request.form.get("track_ids")
    user_id = session.get("user_id")
    
    if user_id and track_ids:
        db.playlists.insert_one({
            "user_id": user_id,
            "tracks": track_ids.split(","),
            "created_at": datetime.datetime.now(datetime.timezone.utc)
        })

    # TODO: save to Spotify via Spotipy API
    from flask import flash
    flash("Playlist saved!", "success")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)