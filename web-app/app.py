import os
import requests
from flask import Flask, render_template, redirect, request, url_for, flash
from flask_bcrypt import Bcrypt
from datetime import datetime, date
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from db import (
    create_indexes,
    find_user_by_username,
    insert_user,
    insert_task,
    get_tasks_for_user,
    mark_task_complete,
    delete_task,
    find_user_by_id,
    update_user_profile,
    delete_user_profile,
    update_task,  # ✅ NEW (you need to add this in db.py)
    find_task_by_id,  # ✅ NEW (you need to add this in db.py)
)
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-this")

bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

ML_CLIENT_URL = os.getenv("ML_CLIENT_URL", "http://localhost:8081")


# =========================
# USER MODEL
# =========================
class User(UserMixin):
    def __init__(self, user_doc: dict):
        self.id = str(user_doc["_id"])
        self.username = user_doc["username"]
        self.email = user_doc["email"]


@login_manager.user_loader
def load_user(user_id: str):
    user_doc = find_user_by_id(user_id)
    if not user_doc:
        return None
    return User(user_doc)


@app.before_request
def setup_database():
    create_indexes()


# =========================
# AUTH ROUTES
# =========================
@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not username or not email or not password:
        flash("All fields are required.")
        return redirect(url_for("register"))

    if find_user_by_username(username):
        flash("That username is already taken.")
        return redirect(url_for("register"))

    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    user_id = insert_user(username=username, email=email, hashed_password=hashed_password)

    user_doc = find_user_by_id(user_id)
    login_user(User(user_doc))

    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    user_doc = find_user_by_username(username)
    if not user_doc:
        flash("Invalid username or password.")
        return redirect(url_for("login"))

    if not bcrypt.check_password_hash(user_doc["password"], password):
        flash("Invalid username or password.")
        return redirect(url_for("login"))

    login_user(User(user_doc))
    return redirect(url_for("dashboard"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# =========================
# DASHBOARD
# =========================
@app.route("/dashboard")
@login_required
def dashboard():
    tasks = get_tasks_for_user(current_user.id)
    return render_template("dashboard.html", tasks=tasks)


# =========================
# PROFILE
# =========================
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user_doc = find_user_by_id(current_user.id)

    if request.method == "GET":
        return render_template("profile.html", user=user_doc)

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()

    if not username or not email:
        flash("Username and email are required.")
        return redirect(url_for("profile"))

    existing_user = find_user_by_username(username)
    if existing_user and str(existing_user["_id"]) != current_user.id:
        flash("That username is already taken.")
        return redirect(url_for("profile"))

    update_user_profile(current_user.id, username, email)
    flash("Profile updated.")
    return redirect(url_for("profile"))


@app.route("/profile/delete", methods=["POST"])
@login_required
def delete_profile():
    delete_user_profile(current_user.id)
    logout_user()
    flash("Your profile has been deleted.")
    return redirect(url_for("login"))


# =========================
# CREATE TASK
# =========================
@app.route("/create", methods=["GET", "POST"])
@login_required
def create_task():
    if request.method == "GET":
        return render_template("create_task.html")

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    due_date = request.form.get("due_date", "").strip()

    if not title or not description or not due_date:
        flash("Title, description, and due date are required.")
        return redirect(url_for("create_task"))

    try:
        due = datetime.strptime(due_date, "%Y-%m-%d").date()

        if due < date.today():
            flash("Due date cannot be in the past.")
            return redirect(url_for("create_task"))

        days_to_complete = (due - date.today()).days
    except ValueError:
        flash("Invalid due date.")
        return redirect(url_for("create_task"))

    priority = get_priority_from_ml_client(title, description, days_to_complete)

    insert_task(
        user_id=current_user.id,
        title=title,
        description=description,
        due_date=due_date,  # ✅ IMPORTANT (you weren’t saving this before)
        priority=priority
    )

    return redirect(url_for("dashboard"))


# =========================
# ✅ EDIT TASK (NEW)
# =========================
@app.route("/edit_task/<task_id>", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    task = find_task_by_id(task_id, current_user.id)

    if not task:
        flash("Task not found.")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due_date = request.form.get("due_date", "").strip()

        if not title or not description or not due_date:
            flash("All fields are required.")
            return redirect(url_for("edit_task", task_id=task_id))

        try:
            due = datetime.strptime(due_date, "%Y-%m-%d").date()
            days_to_complete = (due - date.today()).days
        except ValueError:
            flash("Invalid due date.")
            return redirect(url_for("edit_task", task_id=task_id))

        # ✅ recompute priority
        priority = get_priority_from_ml_client(title, description, days_to_complete)

        update_task(
            task_id=task_id,
            user_id=current_user.id,
            title=title,
            description=description,
            due_date=due_date,
            priority=priority
        )

        return redirect(url_for("dashboard"))

    return render_template("edit_task.html", task=task)


# =========================
# TASK ACTIONS
# =========================
@app.route("/complete/<task_id>", methods=["POST"])
@login_required
def complete_task(task_id):
    if not mark_task_complete(task_id, current_user.id):
        flash("Task could not be completed.")
    return redirect(url_for("dashboard"))


@app.route("/delete/<task_id>", methods=["POST"])
@login_required
def remove_task(task_id):
    if not delete_task(task_id, current_user.id):
        flash("Task could not be deleted.")
    return redirect(url_for("dashboard"))


# =========================
# ML PRIORITY
# =========================
def get_priority_from_ml_client(title: str, description: str, days_to_complete: int) -> str:
    try:
        response = requests.post(
            f"{ML_CLIENT_URL}/api/get_priority_score",
            json={
                "task_description": f"{title}. {description}",
                "task_days_to_complete": days_to_complete
            },
            timeout=10,
        )

        response.raise_for_status()
        score = int(response.json().get("score", 5))

        if score >= 8:
            return "High"
        elif score >= 4:
            return "Medium"
        else:
            return "Low"

    except Exception:
        return "Medium"


# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)