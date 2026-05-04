import bcrypt
from bson import ObjectId
from flask import Blueprint, redirect, render_template, request, session, url_for
from db import mongo

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", error=None)

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    user = mongo.db.users.find_one({"email": email})
    if not user or not bcrypt.checkpw(password.encode(), user["password_hash"]):
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"] = str(user["_id"])
    session["username"] = user["username"]
    return redirect(url_for("movies.home"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html", error=None)

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not username or not email or not password:
        return render_template("register.html", error="All fields are required.")

    if len(password) < 6:
        return render_template("register.html", error="Password must be at least 6 characters.")

    if mongo.db.users.find_one({"email": email}):
        return render_template("register.html", error="An account with that email already exists.")

    if mongo.db.users.find_one({"username": username}):
        return render_template("register.html", error="That username is taken.")

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    result = mongo.db.users.insert_one({
        "username": username,
        "email": email,
        "password_hash": password_hash,
    })

    session["user_id"] = str(result.inserted_id)
    session["username"] = username
    return redirect(url_for("movies.home"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
