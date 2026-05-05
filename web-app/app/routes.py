"""Routes for the meme generator Flask app."""

from flask import Blueprint, render_template, request, redirect, url_for
from bson import ObjectId
from dotenv import load_dotenv

from .db import get_collection

load_dotenv(dotenv_path="../.env")

main = Blueprint("main", __name__)

collection = get_collection()


def _get_collection():
    """Return the configured collection or raise a route-level error."""
    configured_collection = collection if collection is not None else get_collection()
    if configured_collection is None:
        raise RuntimeError(
            "MongoDB is not configured. Set MONGODB_URI to enable history."
        )

    return configured_collection


def check_url(url):
    """Return whether a URL was provided."""
    return url != ""


def make_request_data(url):
    """Build request data for backend calls."""
    if url == "":
        raise ValueError("url is missing")

    return {"url": url}


def show_error(message):
    """Return a simple error message."""
    return "error: " + message


# Home
@main.route("/")
def index():
    """Render homepage with all memes."""
    docs = list(_get_collection().find().sort("created_at", -1))

    for doc in docs:
        doc["_id"] = str(doc["_id"])

    return render_template("index.html", memes=docs)


# Debug route
@main.route("/debug")
def debug():
    """Return test DB entry for debugging."""
    docs = list(_get_collection().find())
    return {"count": len(docs), "sample": str(docs[:1])}


#  Meme detail page
@main.route("/meme/<meme_id>")
def meme_detail(meme_id):
    """Show a single meme."""
    doc = _get_collection().find_one({"_id": ObjectId(meme_id)})

    if not doc:
        return "Not found", 404

    doc["_id"] = str(doc["_id"])

    return render_template("detail.html", meme=doc)


#  Gallery
@main.route("/gallery")
def gallery():
    """Show all memes present in the DB."""
    memes = list(_get_collection().find().sort("created_at", -1))
    return render_template("gallery.html", memes=memes)


#  Submit form
@main.route("/submit", methods=["POST"])
def submit():
    """Insert info to be passed to models to generate memes."""
    name = request.form.get("name")
    url = request.form.get("article-link")
    text = request.form.get("article-text")

    doc = {
        "person_name": name,
        "source_url": url,
        "article_text": text,
    }

    _get_collection().insert_one(doc)

    return redirect(url_for("main.gallery"))
