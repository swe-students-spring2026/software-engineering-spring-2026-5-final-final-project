from flask import Blueprint, render_template, session

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/history")
def history():
    return render_template(
        "history.html",
        history=session.get("recommendation_history", []),
    )


@dashboard_bp.route("/analytics")
def analytics():
    history_items = session.get("recommendation_history", [])
    watchlist_count = len(session.get("watchlist", []))
    recommendation_count = sum(
        1 for item in history_items if item.get("type") == "Recommendation"
    )
    search_count = sum(1 for item in history_items if item.get("type") == "Search")
    semantic_count = sum(1 for item in history_items if item.get("mode") == "intent")

    stats = {
        "total_activity": len(history_items),
        "recommendation_count": recommendation_count,
        "search_count": search_count,
        "semantic_count": semantic_count,
        "watchlist_count": watchlist_count,
    }
    return render_template("analytics.html", stats=stats, history=history_items[:5])
