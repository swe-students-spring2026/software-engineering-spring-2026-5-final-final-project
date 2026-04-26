# main entry point for the web app
import datetime
import os
import re

import pymongo
from bson.objectid import ObjectId
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from datetime import timedelta
from flask import Flask, render_template, request
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
    scope="playlist-modify-public playlist-modify-private",
)
