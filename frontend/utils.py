from bson import ObjectId
from flask import session

from db import mongo


def get_user_id():
    uid = session.get("user_id")
    return ObjectId(uid) if uid else None


def get_watchlist_ids(user_id) -> set[str]:
    if not user_id:
        return set()
    docs = mongo.db.watchlists.find({"user_id": user_id}, {"movie_id": 1})
    return {doc["movie_id"] for doc in docs}
