"""Routes for the meme generator Flask app."""

import json
import os

import requests
from flask import Blueprint, render_template, request, redirect, url_for
from bson import ObjectId
from dotenv import load_dotenv

from .db import get_collection

load_dotenv(dotenv_path="../.env")

SUPPORTED_TEMPLATES = ["buzz", "drake", "ds", "wonka", "fry", "doge"]

main = Blueprint("main", __name__)

collection = None
ML_URL = os.getenv("ML_URL", "http://ml:8000").rstrip("/")


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


def get_ml_error_detail(exc):
    """Extract an ML service error detail from a requests exception."""
    response = exc.response
    if response is None:
        return ""

    try:
        return response.json().get("detail", "")
    except (ValueError, AttributeError):
        try:
            return json.loads(response.text).get("detail", "")
        except (ValueError, AttributeError):
            return response.text


def is_article_extraction_error(message):
    """Return whether the ML error came from URL article extraction."""
    return "Could not extract article from URL" in message


def premium_article_message():
    """Return the message shown when URL article text cannot be read."""
    return (
        "This article may be available only to premium users, behind a login, "
        "or blocked from automatic reading. Paste the article text instead."
    )


def generate_meme_record(name, url, text, template=None):
    """Request meme generation from the ML service."""
    source_url = (url or "").strip()
    article_text = (text or "").strip()
    template_id = (template or "").strip()

    if not source_url and not article_text:
        raise ValueError("Article text or URL is required")

    payload = {
        "person_name": (name or "").strip() or "Anonymous",
        "source_url": source_url or None,
        "text": article_text or None,
        "template": template_id if template_id in SUPPORTED_TEMPLATES else "buzz",
    }
    response = requests.post(f"{ML_URL}/generate", json=payload, timeout=90)
    response.raise_for_status()
    return response.json()


# Home
@main.route("/")
def index():
    """Render homepage with all memes."""
    docs = list(_get_collection().find().sort("created_at", -1))

    for doc in docs:
        doc["_id"] = str(doc["_id"])

    return render_template("index.html", memes=docs, templates=SUPPORTED_TEMPLATES)


@main.route("/health")
def health():
    """Return readiness status without requiring downstream services."""
    return {"status": "ok"}


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
    template = request.form.get("template")

    try:
        generate_meme_record(name, url, text, template)
    except ValueError as exc:
        return show_error(str(exc)), 400
    except requests.RequestException as exc:
        error_detail = get_ml_error_detail(exc)
        print(f"ML service request failed: {exc} {error_detail}", flush=True)
        if is_article_extraction_error(error_detail):
            return (
                render_template(
                    "index.html",
                    error=premium_article_message(),
                    templates=SUPPORTED_TEMPLATES,
                ),
                400,
            )
        return show_error("Could not generate meme. Check web-app and ml logs."), 502

    return redirect(url_for("main.gallery"))
