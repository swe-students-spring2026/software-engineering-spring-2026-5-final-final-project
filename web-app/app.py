"""Web app for the project"""

from curses import flash
import os

from requests import session
from tomlkit import datetime
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
)
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    # current_user,
)
from bson.objectid import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv(override=True)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev")

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
    profs = list(
        professors.find({}, {"name": 1, "title": 1, "email": 1}) # debug
        .sort("name", 1)
        .limit(200)
    )
    for p in profs:
        p["_id"] = str(p.get("_id", ""))
    return render_template("home.html", professors=profs)

# @app.route("")

# ======================== Group routes ========================

@app.route("/groups", methods = ["GET"])
def groups_page():
    """Render the groups page showing all groups the user is a member of."""

    user_id = ObjectId(session["user_id"])
    my_groups = list(groups.find({"members": user_id},{"name": 1, "description": 1, "owner_id": 1, "members": 1})) # we need to include the members field in the mongodb res.
    for g in my_groups:
        g["member_count"] = len(g.get("members", []))
        g["is_owner"] = (g.get("owner_id") == user_id)
    return render_template("groups.html", groups=my_groups)


@app.route("/create_group", methods = ["GET"])
def create_group():
    """Render the create group page for users to create a new group."""

    return render_template("create-group.html")
    
@app.route("/create_group", methods = ["POST"])
def create_group_post():
    """Handle the creation of a new group based on user input from the create group form."""

    group_name = request.form.get("group_name", "").strip()
    group_description = request.form.get("group_description", "").strip()

    if not group_name or not group_description:
        flash("Please enter group name and description.")
        return redirect(url_for("create_group"))
        
    owner_id = ObjectId(session["user_id"])

    groups.insert_one({
        "name": group_name,
        "description": group_description,
        "owner_id": owner_id,
        "members": [owner_id]
    })
    flash("Group created successfully.")
    return redirect(url_for("groups_page"))
    
@app.route("/join_group", methods = ["GET"])
def join_group_form():
    """Render the join group page for users to enter a group ID to join an existing group."""

    return render_template("join-group.html")
    
@app.route("/join_group", methods=["POST"])
def join_group():
    """Handle the user joining a group based on the group ID entered in the join group form."""

    user_oid = ObjectId(session["user_id"])
    group_id = request.form.get("group_id", "").strip()

    try:
        gid = ObjectId(group_id)
    except Exception:
        flash("Invalid group id.")
        return redirect(url_for("join_group_form"))

    group = groups.find_one({"_id": gid})
    if not group:
        flash("Group not found.")
        return redirect(url_for("join_group_form"))

    result = groups.update_one(
    {"_id": gid},
    {"$addToSet": {"members": user_oid}}
    )

    if result.modified_count == 0:
        flash("You are already a member of this group.")
    else:
        flash("Joined group successfully.")

    return redirect(url_for("groups_page"))


@app.route("/review", methods=["GET"])
def my_reviews():
    """Render the page showing all reviews authored by the logged-in user."""

    user_id = ObjectId(session["user_id"])
    my_reviews = list(reviews.find({"author_id": user_id}))
    prof_ids = [r["professor_id"] for r in my_reviews if r.get("professor_id")]
    prof_map = {x["_id"]: x["name"] for x in professors.find({"_id": {"$in": prof_ids}}, {"name": 1})} if prof_ids else {}
    for r in my_reviews:
        r["professor_name"] = prof_map.get(r.get("professor_id"), "Unknown")
    return render_template("my-reviews.html", reviews=my_reviews)

@app.route("/review/new", methods=["GET"])
def review():
    """Render the page for creating a new review, including the list of groups the user is a member of for optional association with the review."""

    user_oid = ObjectId(session["user_id"])

    my_groups = list(groups.find(
    {"members": user_oid},
    {"name": 1}
    ))

    return render_template("review.html", groups=my_groups, form_action=url_for("review_post"))

@app.route("/review/new", methods=["POST"])
def review_post():
    """Handle the submission of a new review based on user input from the review form, including optional association with a group."""

    professor_name = request.form.get("professor_name", "").strip()
    review_text = request.form.get("review_text", "").strip()
    rating = int(request.form.get("rating", "0"))
    group = request.form.get("group_id", "").strip()
    gid = ObjectId(group) if group else None


    if not review_text or not professor_name:
        flash("Please enter a professor name and your review text.")
        return redirect(url_for("review"))
        
    prof = professors.find_one({"name": professor_name})
    if not prof:
        prof_id = professors.insert_one({
        "name": professor_name,
        }).inserted_id
    else:
        prof_id = prof["_id"]

    reviews.insert_one({
        "text": review_text,
        "professor_id": prof_id,
        "rating": rating,
        "author_id": ObjectId(session["user_id"]),
        "created_at": datetime.datetime.utcnow(),
        "updated_at": datetime.datetime.utcnow(),
        "group_id": gid
    })

    flash("Review submitted successfully.")
    return redirect(url_for("my_reviews"))
    
@app.route("/review/<review_id>/delete", methods=["POST"])
def delete_review(review_id):
    """Handle the deletion of a review by its ID, ensuring that only the author of the review can delete it."""

    try:
        rid = ObjectId(review_id)
    except Exception:
        flash("Invalid review id.")
        return redirect(url_for("my_reviews"))

    result = reviews.delete_one({"_id": rid, "author_id": ObjectId(session["user_id"])})
    flash("Review deleted successfully.")
    return redirect(url_for("my_reviews"))

@app.route("/review/<review_id>", methods=["GET"])
def view_review(review_id):
    """Render the page for viewing a specific review by its ID, including the professor's name and any associated group information."""

    try:
        rid = ObjectId(review_id)
    except Exception:
        flash("Invalid review id.")
        return redirect(url_for("my_reviews"))

    review = reviews.find_one({"_id": rid})
    if not review:
        flash("Review not found.")
        return redirect(url_for("my_reviews"))
    
    prof = professors.find_one({"_id": review["professor_id"]}, {"name": 1}) if review.get("professor_id") else None
    review["professor_name"] = prof["name"] if prof else "Unknown"
    return render_template("view-review.html", review=review)
    
@app.route("/review/<review_id>/edit", methods=["GET"])
def edit_review_form(review_id):
    """Render the page for editing a specific review by its ID, pre-populating the form with the existing review information and including the list of groups the user is a member of for optional reassociation with the review."""

    try:
        rid = ObjectId(review_id)
    except Exception:
        flash("Invalid review id.")
        return redirect(url_for("my_reviews"))

    review = reviews.find_one({"_id": rid})
    if not review:
        flash("Review not found.")
        return redirect(url_for("my_reviews"))
    if review.get("author_id") != ObjectId(session["user_id"]):
        flash("You can only edit your own reviews.")
        return redirect(url_for("my_reviews"))
    prof = professors.find_one({"_id": review["professor_id"]}, {"name": 1}) if review.get("professor_id") else None
    review["professor_name"] = prof["name"] if prof else "Unknown"
    my_groups = list(groups.find({"members": ObjectId(session["user_id"])}, {"name": 1}))
    return render_template("review.html", review=review, groups=my_groups, form_action=url_for("edit_review", review_id=review_id),
    mode="edit")

@app.route("/review/<review_id>/edit", methods=["POST"])
def edit_review(review_id):
    """Handle the submission of edits to a specific review by its ID, ensuring that only the author of the review can make edits and allowing for updates to the professor name, review text, rating, and associated group."""

    try:
        rid = ObjectId(review_id)
    except Exception:
        flash("Invalid review id.")
        return redirect(url_for("my_reviews"))

    existing = reviews.find_one({"_id": rid, "author_id": ObjectId(session["user_id"])})
    if not existing:
        flash("Review not found or you can only edit your own reviews.")
        return redirect(url_for("my_reviews"))
        
    professor_name = request.form.get("professor_name", "").strip()
    review_text = request.form.get("review_text", "").strip()
    group = request.form.get("group_id", "").strip()
    rating_raw = request.form.get("rating", "").strip()
    try:
        rating = int(rating_raw) if rating_raw != "" else None
    except ValueError:
        rating = None
    gid = ObjectId(group) if group else None

    if not review_text or not professor_name:
        flash("Please enter a professor name and your review text.")
        return redirect(url_for("edit_review_form", review_id=review_id))

    prof = professors.find_one({"name": professor_name})
    if not prof:
        prof_id = professors.insert_one({
        "name": professor_name,
        }).inserted_id
    else:
        prof_id = prof["_id"]

    reviews.update_one(
        {"_id": rid},
        {"$set": {
            "text": review_text,
            "professor_id": prof_id,
            "rating": rating,
            "updated_at": datetime.datetime.utcnow(),
            "group_id": gid
        }})
        
    flash("Review updated successfully.")

    return redirect(url_for("my_reviews"))


@app.route("/professor/<professor_id>", methods=["GET"])
def professor_details(professor_id):
    """Render the professor details page for a specific professor by their ID, including all reviews for that professor with optional filtering by groups the user is a member of."""
    
    try:
        pid = ObjectId(professor_id)
    except Exception:
        flash("Invalid professor id.")
        return redirect(url_for("home"))

    professor = professors.find_one({"_id": pid})
    if not professor:
        flash("Professor not found.")
        return redirect(url_for("home"))

    selected_group_id = request.args.get("group_id", "").strip()

    user_oid = ObjectId(session["user_id"])
    filter_groups = list(groups.find({"members": user_oid}, {"name": 1}))

    review_filter = {"professor_id": pid}

    if selected_group_id:
        try:
            gid = ObjectId(selected_group_id)
        except Exception:
            flash("Invalid group filter.")
            return redirect(url_for("professor_details", professor_id=professor_id))

        my_group_ids = [g["_id"] for g in filter_groups]
        if gid not in my_group_ids:
            flash("You are not a member of this group.")
            return redirect(url_for("professor_details", professor_id=professor_id))

        review_filter["group_id"] = gid

    professor_reviews = list(reviews.find(review_filter))

    # users
    user_ids = {r["author_id"] for r in professor_reviews}
    user_map = {
        u["_id"]: u["username"]
        for u in users.find({"_id": {"$in": list(user_ids)}})
    }

    # groups
    group_ids = {r["group_id"] for r in professor_reviews}
    group_map = {
        g["_id"]: g["name"]
        for g in groups.find({"_id": {"$in": list(group_ids)}})
    }

    for r in professor_reviews:
        r["author_name"] = user_map.get(r["author_id"], "Unknown")
        r["group_name"] = group_map.get(r["group_id"], "Unknown")

    return render_template(
    "professor-detail.html",
    professor=professor,
    reviews=professor_reviews,
    review_count=len(professor_reviews),
    filter_groups=filter_groups,
    selected_group_id=selected_group_id
)

if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")
