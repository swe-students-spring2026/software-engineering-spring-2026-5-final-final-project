from flask import Blueprint, render_template, request
from services.search_router import handle_search
from services.api_client import get_movie_details

movies_bp = Blueprint("movies", __name__)


@movies_bp.route("/")
def home():
    return render_template("home.html")


@movies_bp.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return render_template("results.html", results=[], query="", mode=None)

    search_data = handle_search(query)
    return render_template(
        "results.html",
        results=search_data["results"],
        query=search_data["query"],
        mode=search_data["mode"],
    )


@movies_bp.route("/movie/<movie_id>")
def movie_detail(movie_id):
    movie = get_movie_details(movie_id)
    return render_template("movie_detail.html", movie=movie)
