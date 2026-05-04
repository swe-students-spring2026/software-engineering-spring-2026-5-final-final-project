from bson import ObjectId
from flask import Blueprint, render_template, session

from db import mongo

dashboard_bp = Blueprint("dashboard", __name__)


def _user_id():
    uid = session.get("user_id")
    return ObjectId(uid) if uid else None


def _get_history(user_id):
    if not user_id:
        return []
    docs = mongo.db.history.find(
        {"user_id": user_id},
        sort=[("timestamp", -1)],
        limit=20,
    )
    return list(docs)


@dashboard_bp.route("/history")
def history():
    items = _get_history(_user_id())
    return render_template("history.html", history=items)


@dashboard_bp.route("/analytics")
def analytics():
    user_id = _user_id()
    history_items = _get_history(user_id)

    watchlist_count = mongo.db.watchlists.count_documents({"user_id": user_id}) if user_id else 0
    recommendation_count = sum(1 for i in history_items if i.get("type") == "Recommendation")
    search_count = sum(1 for i in history_items if i.get("type") == "Search")
    semantic_count = sum(1 for i in history_items if i.get("mode") == "intent")

    stats = {
        "total_activity": len(history_items),
        "recommendation_count": recommendation_count,
        "search_count": search_count,
        "semantic_count": semantic_count,
        "watchlist_count": watchlist_count,
    }
    return render_template("analytics.html", stats=stats, history=history_items[:5])
