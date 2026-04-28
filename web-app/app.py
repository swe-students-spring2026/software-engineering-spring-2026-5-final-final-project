"""Web app for the project"""

import os
import datetime

from flask import (
    Flask,
    flash,
    render_template,
    request,
    session,
    redirect,
    url_for,
    jsonify,
)
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from bson.objectid import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from pymongo import MongoClient
from difflib import SequenceMatcher
import re
import requests as http_requests

# Load environment variables
if os.getenv("APP_ENV") != "docker":
    load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev")
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://localhost:5001/analyze")

# MongoDB connection
mongo_uri = os.getenv("MONGO_URI")
mongo_dbname = os.getenv("MONGO_DBNAME", "potatoes")
if not mongo_uri:
    raise RuntimeError("MONGO_URI must be set in .env to connect to MongoDB.")
client = MongoClient(
    mongo_uri,
    serverSelectionTimeoutMS=3000,
    connectTimeoutMS=3000,
    socketTimeoutMS=5000,
)
db = client[mongo_dbname]
users = db["users"]
groups = db["groups"]
reviews = db["reviews"]
professors = db["professors"]
posts = db["posts"]

def _refresh_user_rated_professors(*, user_oid: ObjectId, author_email: str) -> list[ObjectId]:
    professor_ids = [x for x in posts.distinct("professor_id", {"author_email": author_email}) if x]
    users.update_one(
        {"_id": user_oid},
        {"$set": {"rated_professor_ids": professor_ids, "professors_rated": len(professor_ids)}},
    )
    return professor_ids

# Flask login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # redirect here if not logged in


class User(UserMixin):
    """Represents a user for Flask-Login integration."""

    def __init__(self, user):
        self.id = user["_id"]
        self.email = user["email"]
        self.password = user["password"]


@login_manager.user_loader
def load_user(user_id):
    """Load a user from the database by their user ID for Flask-Login integration."""
    # session stores user's _id; load user by _id
    try:
        oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
        user = db.users.find_one({"_id": oid})
        if user:
            return User(user)
    except (InvalidId, ValueError):
        pass
    return None

@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login via GET and POST requests."""
    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")

        # check the database
        user = db.users.find_one({"email": email})
        if user and user["password"] == password:
            login_user(User(user))

            return redirect(url_for("home"))

        return render_template("login.html", error="Invalid email or password.")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Handle user signup via GET and POST requests."""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if db.users.find_one({"email": email}):
            return render_template("signup.html", error="Email already taken.")

        db.users.insert_one({"email": email, "password": password})

        return redirect(url_for("login"))
    return render_template("signup.html")


@app.route("/logout")
@login_required
def logout():
    """Handle user logout and redirect to login page."""
    logout_user()
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def home():
    """Render the home page for logged-in users."""
    user_oid = ObjectId(current_user.id) if isinstance(current_user.id, str) else current_user.id

    post_count = posts.count_documents({"author_email": current_user.email})
    user_doc = users.find_one({"_id": user_oid}, {"professors_rated": 1, "rated_professor_ids": 1}) or {}
    rated_ids = user_doc.get("rated_professor_ids")
    if not isinstance(rated_ids, list):
        rated_ids = _refresh_user_rated_professors(user_oid=user_oid, author_email=current_user.email)
    else:
        # Keep the count in sync with posts even if the user doc was stale.
        rated_ids = _refresh_user_rated_professors(user_oid=user_oid, author_email=current_user.email)

    prof_names = [
        p.get("name", "")
        for p in professors.find({"_id": {"$in": rated_ids}}, {"name": 1}).sort("name", 1)
        if p.get("name")
    ]

    user_stats = {
        "post_count": post_count,
        "professors_rated": int(user_doc.get("professors_rated") or len(rated_ids)),
    }

    my_posts = list(
        posts.find(
            {"author_email": current_user.email},
            {"professor_name": 1, "text": 1, "created_at": 1, "professor_id": 1},
        )
        .sort("created_at", -1)
        .limit(300)
    )

    grouped: dict[str, list[dict]] = {}
    for p in my_posts:
        pname = p.get("professor_name") or "Unknown"
        grouped.setdefault(pname, []).append(
            {
                "text": p.get("text", ""),
                "created_at": p.get("created_at"),
                "professor_id": str(p.get("professor_id", "")) if p.get("professor_id") else "",
            }
        )

    my_posts_by_prof = [
        {"professor_name": name, "posts": grouped[name]}
        for name in sorted(grouped.keys())
    ]

    return render_template(
        "home.html",
        user=user_stats,
        rated_professors=prof_names,
        my_posts_by_prof=my_posts_by_prof,
    )


def _normalize_query(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _name_score(query: str, name: str) -> float:
    q = _normalize_query(query)
    n = _normalize_query(name)
    if not q or not n:
        return 0.0
    if q == n:
        return 10.0
    score = SequenceMatcher(None, q, n).ratio()
    if n.startswith(q):
        score += 1.0
    if q in n:
        score += 0.5
    return score


@app.route("/api/professors/search", methods=["GET"])
@login_required
def professors_search():
    q = request.args.get("q", "")
    qn = _normalize_query(q)
    if not qn:
        return jsonify({"results": []})

    regex = re.compile(re.escape(qn), re.IGNORECASE)
    candidates = list(
        professors.find(
            {"name": {"$regex": regex}},
            {"name": 1, "title": 1, "email": 1},
        ).limit(200)
    )

    if len(candidates) < 5:
        # Fallback to a broader pool for "closest match" ranking.
        candidates = list(
            professors.find({}, {"name": 1, "title": 1, "email": 1})
            .limit(400)
        )

    ranked = sorted(
        candidates,
        key=lambda p: _name_score(qn, p.get("name", "")),
        reverse=True,
    )

    results = []
    for p in ranked[:10]:
        results.append(
            {
                "id": str(p.get("_id", "")),
                "name": p.get("name", ""),
                "title": p.get("title", ""),
                "email": p.get("email", ""),
            }
        )
    return jsonify({"results": results})


@app.route("/professors/<professor_id>", methods=["GET"])
@login_required
def professor_page(professor_id):
    try:
        pid = ObjectId(professor_id)
    except (InvalidId, ValueError):
        flash("Invalid professor id.")
        return redirect(url_for("home"))

    prof = professors.find_one({"_id": pid}, {"name": 1, "title": 1, "email": 1, "sentiment_overall": 1, "sentiment_themes": 1, "sentiment_post_count": 1})
    if not prof:
        flash("Professor not found.")
        return redirect(url_for("home"))

    prof["_id"] = str(prof["_id"])
    prof_posts = list(
        posts.find({"professor_id": pid}, {"text": 1, "author_email": 1, "created_at": 1, "updated_at": 1, "sentiment": 1})
        .sort("created_at", -1)
        .limit(200)
    )
    for p in prof_posts:
        p["_id"] = str(p.get("_id", ""))
    return render_template("professor.html", professor=prof, posts=prof_posts)


@app.route("/professors/<professor_id>/posts/new", methods=["GET"])
@login_required
def new_post_form(professor_id):
    try:
        pid = ObjectId(professor_id)
    except (InvalidId, ValueError):
        flash("Invalid professor id.")
        return redirect(url_for("home"))

    prof = professors.find_one({"_id": pid}, {"name": 1})
    if not prof:
        flash("Professor not found.")
        return redirect(url_for("home"))

    return render_template(
        "post-edit.html",
        professor_id=str(pid),
        professor_name=prof.get("name", ""),
        post_text="",
        form_action=url_for("new_post_submit", professor_id=str(pid)),
    )

def _get_sentiment(text: str) -> dict | None:
    try:
        resp = http_requests.post(ML_SERVICE_URL, data={"feedback": text}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None

def _polarity_to_label(polarity: float) -> str:
    if polarity >= 0.35:
        return "Very Positive"
    elif polarity >= 0.1:
        return "Positive"
    elif polarity > -0.1:
        return "Neutral"
    elif polarity > -0.35:
        return "Negative"
    else:
        return "Very Negative"

def _update_professor_sentiment(professor_id: ObjectId) -> None:
    all_posts = list(posts.find(
        {"professor_id": professor_id, "sentiment": {"$exists": True}},
        {"sentiment": 1}
    ))
    if not all_posts:
        return

    # Aggregate overall score
    overall_scores = [p["sentiment"]["overall"]["score"] for p in all_posts]
    avg_overall = round(sum(overall_scores) / len(overall_scores), 1)
    avg_label = _polarity_to_label((avg_overall / 50) - 1)  # map 0-100 back to polarity

    # Aggregate per-theme scores across all posts
    theme_totals: dict[str, list[float]] = {}
    for p in all_posts:
        for t in p["sentiment"].get("themes", []):
            theme_totals.setdefault(t["theme"], []).append(t["score"])

    theme_aggregates = [
        {
            "theme": theme,
            "score": round(sum(scores) / len(scores), 1),
            "label": _polarity_to_label((round(sum(scores) / len(scores), 1) / 50) - 1),
        }
        for theme, scores in theme_totals.items()
    ]
    theme_aggregates.sort(key=lambda x: x["score"], reverse=True)

    professors.update_one(
        {"_id": professor_id},
        {"$set": {
            "sentiment_overall": {"score": avg_overall, "label": avg_label},
            "sentiment_themes": theme_aggregates,
            "sentiment_post_count": len(all_posts),
        }}
    )


@app.route("/professors/<professor_id>/posts/new", methods=["POST"])
@login_required
def new_post_submit(professor_id):
    try:
        pid = ObjectId(professor_id)
    except (InvalidId, ValueError):
        flash("Invalid professor id.")
        return redirect(url_for("home"))

    prof = professors.find_one({"_id": pid}, {"name": 1})
    if not prof:
        flash("Professor not found.")
        return redirect(url_for("home"))

    text = request.form.get("text", "").strip()
    if not text:
        flash("Post text cannot be empty.")
        return redirect(url_for("new_post_form", professor_id=str(pid)))

    try:
        sentiment = _get_sentiment(text)
    except Exception:
        flash("Failed to analyze sentiment. Please try again later.")
        return redirect(url_for("new_post_form", professor_id=str(pid)))
    
    now = datetime.datetime.utcnow()
    posts.insert_one(
        {
            "professor_id": pid,
            "professor_name": prof.get("name", ""),
            "author_email": getattr(current_user, "email", ""),
            "text": text,
            "created_at": now,
            "updated_at": now,
            "sentiment": sentiment,
        }
    )
    _refresh_user_rated_professors(user_oid=ObjectId(current_user.id), author_email=current_user.email)

    # Recompute professor-level aggregates
    _update_professor_sentiment(pid)

    flash("Post created.")
    return redirect(url_for("professor_page", professor_id=str(pid)))

if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")
