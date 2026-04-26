"""DinnerMeet Flask application."""

import os

from bson import ObjectId
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from models.user import create_user
from models.event_model import create_event
from utils.validation import validate_signup, validate_login, validate_event

load_dotenv()

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
app.secret_key = os.environ.get("SECRET_KEY", "dev")

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data["_id"])
        self.email = user_data["email"]
        self.data = user_data


@login_manager.user_loader
def load_user(user_id):
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if user:
        return User(user)
    return None


@app.route("/")
@login_required
def index():
    """Redirect to home or login."""
    #if session.get("user_id"):
    #    return render_template("home.html")
    #return redirect(url_for("login"))
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Render login page."""
    if request.method == "GET":
        return render_template("login.html")
    
    data = request.form
    users_collection = None  # Replace with actual database collection
    
    error, user_data = validate_login(data, users_collection)

    if error:
        return render_template("login.html", error=error)
    
    user = User(user_data)
    login_user(user)

    flash("Logged in successfully.", "success")
    return redirect(url_for("index"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Render signup page. 
    Create a new user and log them in."""
    if request.method == "GET":
        return render_template("signup.html")

    data = request.form

    # Need to implement database then uncomment this to check for existing user
    users_collection = None  # Replace with actual database collection
    error = validate_signup(data, users_collection)
    if error:
        return render_template("signup.html", error=error)

    existing_user = users_collection.find_one({"email": data["email"]})
    if existing_user:
        return render_template("signup.html", error="User already exists.")

    user_data = create_user(data)
    result = users_collection.insert_one(user_data)

    user_data["_id"] = result.inserted_id
    user = User(user_data)
    login_user(user)

    flash("Account created successfully.", "success")
    return redirect(url_for("index"))


@app.route("/logout")
@login_required
def logout():
    """Clear session and redirect to login."""
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/events")
@login_required
def events():
    """Show all events."""
    return render_template("events.html", events=[])


@app.route("/events/create", methods=["GET", "POST"])
@login_required
def create_event_route():
    """Create a new event."""
    if request.method == "GET":
        return render_template("create_event.html")
    
    data = request.form.to_dict()
    data["tags"] = request.form.getlist("tags")  

    error = validate_event(data)
    if error:
        return render_template("create_event.html", error=error)
    
    event = create_event(data, current_user.id) 

    # Replace with actual database collections
    events_collection = None
    users_collection = None

    result = events_collection.insert_one(event)

    users_collection.update_one(
        {"_id": current_user.id},
        {"$push": {"created_events": result.inserted_id}}
    )

    flash("Event created successfully.", "success")
    return redirect(url_for("events"))

@app.route("/profile")
@login_required
def profile():
    """Show user profile."""
    return render_template("home.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)
