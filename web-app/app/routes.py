"""Routes for the meme generator Flask app."""

import os
from flask import Blueprint, render_template, request, redirect, url_for
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")

main = Blueprint("main", __name__)

# MongoDB connection
client = MongoClient(os.getenv("MONGODB_URI"), serverSelectionTimeoutMS=5000)

# print(client.admin.command("ping"))

db = client[os.getenv("MONGODB_DB_NAME")]
collection = db[os.getenv("MONGODB_COLLECTION_NAME")]


# Home
@main.route("/")
def index():
    """Render homepage with all memes."""
    docs = list(collection.find().sort("created_at", -1))

    for doc in docs:
        doc["_id"] = str(doc["_id"])

    return render_template("index.html", memes=docs)


# Debug route
@main.route("/debug")
def debug():
    """Return test DB entry for debugging."""
    docs = list(collection.find())
    return {"count": len(docs), "sample": str(docs[:1])}


#  Meme detail page
@main.route("/meme/<meme_id>")
def meme_detail(meme_id):
    """Show a single meme."""
    doc = collection.find_one({"_id": ObjectId(meme_id)})

    if not doc:
        return "Not found", 404

    doc["_id"] = str(doc["_id"])

    return render_template("detail.html", meme=doc)


#  Gallery
@main.route("/gallery")
def gallery():
    """Show all memes present in the DB."""
    memes = list(collection.find().sort("created_at", -1))
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

    collection.insert_one(doc)

    return redirect(url_for("main.gallery"))
