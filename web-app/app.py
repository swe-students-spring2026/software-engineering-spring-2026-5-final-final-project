import os
import requests
from flask import Flask, render_template, redirect, request, url_for, flash
from flask_bcrypt import Bcrypt
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
)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-this")

# Initialize Flask-Bcrypt for password hashing
bcrypt = Bcrypt(app)

# Initialize Flask-Login for user sessions
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ML Client URL (You can change this if you have the ML client running somewhere else)
ML_CLIENT_URL = os.getenv("ML_CLIENT_URL", "http://localhost:5001")

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_doc: dict):
        self.id = str(user_doc["_id"])
        self.username = user_doc["username"]
        self.email = user_doc["email"]

# Load user function for Flask-Login
@login_manager.user_loader
def load_user(user_id: str):
    user_doc = find_user_by_username(user_id)
    if not user_doc:
        return None
    return User(user_doc)

# Set up database indexes before every request
@app.before_request
def setup_database():
    create_indexes()

# Home route (Redirects to login if not logged in)
@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

# Register route (GET to show form, POST to handle submission)
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

    # Check if username already exists
    existing_user = find_user_by_username(username)
    if existing_user:
        flash("That username is already taken.")
        return redirect(url_for("register"))

    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    user_id = insert_user(username=username, email=email, hashed_password=hashed_password)

    # Log the user in after registration
    user_doc = find_user_by_username(user_id)
    login_user(User(user_doc))

    return redirect(url_for("dashboard"))

# Login route (GET to show form, POST to handle login)
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    # Find user by username
    user_doc = find_user_by_username(username)
    if not user_doc:
        flash("Invalid username or password.")
        return redirect(url_for("login"))

    # Check password hash
    password_is_correct = bcrypt.check_password_hash(user_doc["password"], password)
    if not password_is_correct:
        flash("Invalid username or password.")
        return redirect(url_for("login"))

    # Log the user in
    login_user(User(user_doc))
    return redirect(url_for("dashboard"))

# Logout route
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# Dashboard route (Lists all tasks for the logged-in user)
@app.route("/dashboard")
@login_required
def dashboard():
    tasks = get_tasks_for_user(current_user.id)
    return render_template("dashboard.html", tasks=tasks)

# Create task route (GET to show form, POST to handle creation)
@app.route("/create", methods=["GET", "POST"])
@login_required
def create_task():
    if request.method == "GET":
        return render_template("create_task.html")

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if not title or not description:
        flash("Title and description are required.")
        return redirect(url_for("create_task"))

    priority = get_priority_from_ml_client(title, description)

    # Insert the task into the database
    insert_task(user_id=current_user.id, title=title, description=description, priority=priority)

    return redirect(url_for("dashboard"))

# Mark task as complete route (POST to update task status)
@app.route("/complete/<task_id>", methods=["POST"])
@login_required
def complete_task(task_id):
    success = mark_task_complete(task_id, current_user.id)
    if not success:
        flash("Task could not be completed.")
    return redirect(url_for("dashboard"))

# Delete task route (POST to remove task)
@app.route("/delete/<task_id>", methods=["POST"])
@login_required
def remove_task(task_id):
    success = delete_task(task_id, current_user.id)
    if not success:
        flash("Task could not be deleted.")
    return redirect(url_for("dashboard"))

# Helper function to call ML Client and get priority
def get_priority_from_ml_client(title: str, description: str) -> str:
    try:
        # Make a POST request to the ML client with the task title and description
        response = requests.post(
            f"{ML_CLIENT_URL}/prioritize",
            json={"title": title, "description": description},
            timeout=5,
        )
        response.raise_for_status()

        # Get priority from ML client response (should be 'High', 'Medium', or 'Low')
        data = response.json()
        priority = data.get("priority", "Medium").title()

        if priority not in {"High", "Medium", "Low"}:
            return "Medium"

        return priority

    except requests.RequestException:
        # If the ML client call fails, return 'Medium' by default
        return "Medium"

# Run the Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
