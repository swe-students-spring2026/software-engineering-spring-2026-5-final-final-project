from datetime import datetime
from urllib.parse import urlparse

from flask import Blueprint, render_template, request, session

from services.api_client import (
    get_movie_details,
    get_similar_movies,
    recommend_from_favorites,
)
from services.search_router import handle_search
from services.api_client import get_movie_details, get_favorites, recommend_movies

movies_bp = Blueprint("movies", __name__)


@movies_bp.route("/")
def home():
    favorites = get_favorites()
    favorite_ids = [m["id"] for m in favorites]
    recommendations = recommend_movies(favorite_ids) if favorite_ids else []
    return render_template("home.html", favorites=favorites, recommendations=recommendations)


@movies_bp.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return render_template(
            "results.html",
            results=[],
            query="",
            mode=None,
            watchlist_ids=_watchlist_ids(),
        )

    search_data = handle_search(query)
    _append_history(
        {
            "type": "Search",
            "query": search_data["query"],
            "mode": search_data["mode"],
            "result_count": len(search_data["results"]),
        }
    )
    return render_template(
        "results.html",
        results=search_data["results"],
        query=search_data["query"],
        mode=search_data["mode"],
        watchlist_ids=_watchlist_ids(),
    )


@movies_bp.route("/recommendations", methods=["POST"])
def recommendations():
    favorite_titles = [
        request.form.get(f"favorite_{index}", "").strip()
        for index in range(1, 5)
    ]
    if any(not title for title in favorite_titles):
        return render_template(
            "home.html",
            error="Please enter four favorite movies before generating recommendations.",
            favorite_titles=favorite_titles,
        )

    results = recommend_from_favorites(favorite_titles)
    _append_history(
        {
            "type": "Recommendation",
            "query": ", ".join(favorite_titles),
            "mode": "cosine",
            "result_count": len(results),
        }
    )
    return render_template(
        "results.html",
        results=results,
        query=", ".join(favorite_titles),
        mode="favorites",
        watchlist_ids=_watchlist_ids(),
    )


@movies_bp.route("/movie/<movie_id>")
def movie_detail(movie_id):
    movie = get_movie_details(movie_id)
    similar_movies = get_similar_movies(movie_id)
    back_url = _safe_back_url(request.args.get("back"), request.referrer)
    return render_template(
        "movie_detail.html",
        movie=movie,
        similar_movies=similar_movies,
        watchlist_ids=_watchlist_ids(),
        back_url=back_url,
    )


def _safe_back_url(param: str | None, referrer: str | None) -> str | None:
    if param and param.startswith("/") and not param.startswith("//"):
        return param
    if referrer:
        parsed = urlparse(referrer)
        rel = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        if rel and rel != request.path:
            return rel
    return None


def _watchlist_ids() -> set[str]:
    return set(session.get("watchlist", []))


def _append_history(entry: dict) -> None:
    history = session.get("recommendation_history", [])
    history.insert(
        0,
        {
            **entry,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        },
    )
    session["recommendation_history"] = history[:20]
