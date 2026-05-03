from flask import Blueprint, redirect, render_template, request, session, url_for

from services.api_client import get_movies_by_ids

favorites_bp = Blueprint("favorites", __name__)


@favorites_bp.route("/favorites")
@favorites_bp.route("/watchlist")
def watchlist():
    saved = get_movies_by_ids(session.get("watchlist", []))
    return render_template("favorites.html", favorites=saved)


@favorites_bp.route("/watchlist/toggle/<movie_id>", methods=["POST"])
def toggle_watchlist(movie_id):
    watchlist_ids = session.get("watchlist", [])
    if movie_id in watchlist_ids:
        watchlist_ids = [saved_id for saved_id in watchlist_ids if saved_id != movie_id]
    else:
        watchlist_ids.append(movie_id)

    session["watchlist"] = watchlist_ids
    return redirect(request.form.get("next") or url_for("favorites.watchlist"))
