import os
from functools import wraps

import requests
from flask import Flask, render_template, session, redirect, url_for, request, flash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

API_URL = os.environ.get("API_URL", "http://localhost:5001")


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html", active_tab="dashboard")


@app.route("/friends")
@login_required
def friends():
    return render_template("friends.html", active_tab="friends")


@app.route("/add")
@login_required
def add_expense():
    return render_template("add_expense.html", active_tab="add")


@app.route("/history")
@login_required
def history():
    return render_template("history.html", active_tab="history")


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", active_tab="profile")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        try:
            resp = requests.post(
                f"{API_URL}/api/login",
                json={"username": username, "password": password},
                timeout=5,
            )
            if resp.status_code == 200:
                session["user"] = resp.json()
                return redirect(url_for("dashboard"))
            flash(resp.json().get("error", "Invalid credentials"))
        except requests.exceptions.RequestException:
            flash("Could not connect to server")
        return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        email = request.form.get("email", "").strip() or None
        try:
            resp = requests.post(
                f"{API_URL}/api/users",
                json={"username": username, "password": password, "email": email},
                timeout=5,
            )
            if resp.status_code == 201:
                session["user"] = resp.json()
                return redirect(url_for("dashboard"))
            flash(resp.json().get("error", "Registration failed"))
        except requests.exceptions.RequestException:
            flash("Could not connect to server")
        return redirect(url_for("register"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
