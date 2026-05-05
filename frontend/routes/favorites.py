from datetime import datetime, timezone

from flask import Blueprint, redirect, render_template, request, url_for

from db import mongo
from services.api_client import get_movies_by_ids
from utils import get_user_id, get_watchlist_ids

favorites_bp = Blueprint("favorites", __name__)


@favorites_bp.route("/favorites")
@favorites_bp.route("/watchlist")
def watchlist():
    user_id = get_user_id()
    movie_ids = get_watchlist_ids(user_id)
    saved = get_movies_by_ids(movie_ids)
    return render_template("favorites.html", favorites=saved)


@favorites_bp.route("/watchlist/toggle/<movie_id>", methods=["POST"])
def toggle_watchlist(movie_id):
    user_id = get_user_id()
    if not user_id:
        return redirect(url_for("auth.login"))

    existing = mongo.db.watchlists.find_one({"user_id": user_id, "movie_id": movie_id})
    if existing:
        mongo.db.watchlists.delete_one({"_id": existing["_id"]})
    else:
        mongo.db.watchlists.insert_one({
            "user_id": user_id,
            "movie_id": movie_id,
            "added_at": datetime.now(timezone.utc),
        })

    return redirect(request.form.get("next") or url_for("favorites.watchlist"))
