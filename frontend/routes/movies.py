from datetime import datetime

from flask import Blueprint, render_template, request, session

from services.api_client import (
    get_movie_details,
    get_similar_movies,
    recommend_from_favorites,
)
from services.search_router import handle_search

movies_bp = Blueprint("movies", __name__)


@movies_bp.route("/")
def home():
    return render_template("home.html")


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
    return render_template(
        "movie_detail.html",
        movie=movie,
        similar_movies=similar_movies,
        watchlist_ids=_watchlist_ids(),
    )


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
