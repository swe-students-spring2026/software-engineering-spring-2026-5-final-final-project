# main entry point for the web app
import datetime
import os
import re

import pymongo
from bson.objectid import ObjectId
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for, session
from datetime import timedelta
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# create the Flask app
app = Flask(__name__)
# load environment variables from .env file
load_dotenv()
# set the secret key for session management
app.secret_key = os.getenv("SECRET_KEY")
# connect to MongoDB
client = pymongo.MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_NAME")]

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
    
    return render_template("index.html", 
        username=user_info["display_name"],
        user_image=user_info["images"][0]["url"] if user_info["images"] else None
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
    # TODO: call ml-client
    return render_template("index.html", username=session.get("user_id"), tracks=[])

@app.route("/save_playlist", methods=["POST"])
def save_playlist():
    # TODO: save to Spotify
    flash("Playlist saved!", "success")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)