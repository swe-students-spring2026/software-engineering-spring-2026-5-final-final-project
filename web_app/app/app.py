import os

from bson.errors import InvalidId
from bson import ObjectId
from flask import Flask, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from pymongo import MongoClient

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    template_folder=os.path.join(base_dir, "templates"),
    static_folder=os.path.join(base_dir, "static"),
)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "sign_in"


def get_db():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    mongo_dbname = os.getenv("MONGO_DBNAME", "flakemate")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
    client.admin.command("ping")
    return client[mongo_dbname]


def get_users_collection():
    return get_db()["users"]


class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data["_id"])
        self.name = user_data.get("name", "")
        self.phone_number = user_data.get("phone_number", "")


@login_manager.user_loader
def load_user(user_id):
    try:
        user = get_users_collection().find_one({"_id": ObjectId(user_id)})
        if user:
            return User(user)
    except (InvalidId, TypeError):
        return None
    return None


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("home_upcoming"))
    return redirect(url_for("sign_in"))


@app.route("/sign-in", methods=["GET", "POST"])
def sign_in():
    if current_user.is_authenticated:
        return redirect(url_for("home_upcoming"))

    error = None

    if request.method == "POST":
        phone_number = request.form.get("phone_number", "").strip()
        password = request.form.get("password", "")

        user = get_users_collection().find_one({"phone_number": phone_number})

        if user and user.get("password") == password:
            login_user(User(user))
            return redirect(url_for("home_upcoming"))

        error = "Invalid phone number or password"

    return render_template("user-sign-in.html", error=error)


@app.route("/create-account", methods=["GET", "POST"])
def create_account():
    if current_user.is_authenticated:
        return redirect(url_for("home_upcoming"))

    error = None

    if request.method == "POST":
        phone_number = request.form.get("phone_number", "").strip()
        password = request.form.get("password", "")
        name = request.form.get("name", "").strip()

        if not phone_number or not password or not name:
            error = "Please fill in all fields."
        else:
            users = get_users_collection()

            if users.find_one({"phone_number": phone_number}):
                error = "User already exists"
            else:
                users.insert_one(
                    {
                        "name": name,
                        "phone_number": phone_number,
                        "password": password,
                        "lateness": [],
                        "events_owned": [],
                        "event_invites": [],
                    }
                )
                return redirect(url_for("sign_in"))

    return render_template("user-create-account.html", error=error)


@app.route("/home-past")
@login_required
def home_past():
    return render_template("home-past.html")


@app.route("/home-upcoming")
@login_required
def home_upcoming():
    return render_template("home-upcoming.html")


@app.route("/invites")
@login_required
def invites():
    return render_template("invites.html")


@app.route("/host-events")
@login_required
def host_events():
    return render_template("host-events.html")


@app.route("/user", methods=["GET", "POST"])
@login_required
def user_dashboard():
    users = get_users_collection()
    user = users.find_one({"_id": ObjectId(current_user.id)})

    if not user:
        logout_user()
        return redirect(url_for("sign_in"))

    error = None
    message = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone_number = request.form.get("phone_number", "").strip()
        password = request.form.get("password", "")

        update_data = {}
        if name:
            update_data["name"] = name
        if phone_number:
            update_data["phone_number"] = phone_number
        if password:
            update_data["password"] = password

        if update_data:
            users.update_one({"_id": ObjectId(current_user.id)}, {"$set": update_data})
            user = users.find_one({"_id": ObjectId(current_user.id)})
            message = "Saved"
        else:
            error = "No changes to save"

    return render_template(
        "user-dashboard.html",
        user=user,
        error=error,
        message=message,
    )


@app.route("/sign-out")
@login_required
def sign_out():
    logout_user()
    return redirect(url_for("sign_in"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)