"""DinnerMeet Flask application."""

import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev")


@app.route("/")
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
    return render_template("login.html", error="Login not yet implemented.")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Render signup page."""
    if request.method == "GET":
        return render_template("signup.html")
    return render_template("signup.html", error="Signup not yet implemented.")


@app.route("/logout")
def logout():
    """Clear session and redirect to login."""
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/events")
def events():
    """Show all events."""
    return render_template("events.html", events=[])


@app.route("/events/create", methods=["GET", "POST"])
def create_event():
    """Create a new event."""
    if request.method == "GET":
        return render_template("create_event.html")
    return render_template("create_event.html", error="Create event not yet implemented.")


@app.route("/profile")
def profile():
    """Show user profile."""
    return render_template("home.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)
