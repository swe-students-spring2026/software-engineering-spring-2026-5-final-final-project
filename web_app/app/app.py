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
from datetime import datetime

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
                        "events_owned": {},
                        "events_accepted": {},
                        "event_invites": {},
                    }
                )
                return redirect(url_for("sign_in"))

    return render_template("user-create-account.html", error=error)

@app.template_filter('format_time')
def format_time(date):

    # make sure there is no 0 before the hour
    hour = date.hour % 12
    if hour == 0:
        hour = 12
    minute = f"{date.minute:02d}"
    am_pm = "AM" if date.hour < 12 else "PM"
    
    # make sure there is no leading 0 before the day
    # also add the suffix to the date (st, nd, etc)
    day = date.day
    if 11 <= day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    
    # get the month and the year
    month = date.strftime("%B")
    year = date.year
    
    # return the datetime
    return f"{hour}:{minute} {am_pm}, {month} {day}{suffix}, {year}"

@app.route("/home-past")
@login_required
def home_past():
    # get current user
    users_collection = get_users_collection()
    user = users_collection.find_one({"_id": ObjectId(current_user.id)})

    # get all of the past events
    current_datetime = datetime.now()
    past_events = []

    user_event_datetimes = {}

    # go through the user's owned events
    if "events_owned" in user and user["events_owned"]:
        if isinstance(user["events_owned"], dict):
            for event_id, event_datetime in user["events_owned"].items():
                if event_datetime < current_datetime:
                    user_event_datetimes[event_id] = event_datetime

    # go through the user's accepted events
    if "events_accepted" in user and user["events_accepted"]:
        if isinstance(user["events_accepted"], dict):
            for event_id, event_datetime in user["events_accepted"].items():
                if event_datetime < current_datetime:
                    user_event_datetimes[event_id] = event_datetime

    # we have to get all of the details for the events
    if user_event_datetimes:
        events_collection = get_db()["events"]
        # go through each event
        for event_id, event_datetime in user_event_datetimes.items():
            event = events_collection.find_one({"_id": ObjectId(event_id)})

            if event:
                past_events.append({
                    "_id": event.get("_id"),
                    "name": event.get("name", "Untitled Event"),
                    "location": event.get("location", "No location specified"),
                    "date": event_datetime,
                    "details": event.get("description", "No description provided")
                })

    # we have to sort the events by the most recent first
    past_events.sort(key=lambda x: x["date"], reverse=True)

    return render_template("home-past.html", past_events = past_events)


@app.route("/home-upcoming")
@login_required
def home_upcoming():
    # get current user
    users_collection = get_users_collection()
    user = users_collection.find_one({"_id": ObjectId(current_user.id)})

    # get all of the upcoming events
    current_datetime = datetime.now()
    upcoming_events = []

    user_event_datetimes = {}

    # go through the user's owned events
    if "events_owned" in user and user["events_owned"]:
        if isinstance(user["events_owned"], dict):
            for event_id, event_datetime in user["events_owned"].items():
                if event_datetime >= current_datetime:
                    user_event_datetimes[event_id] = event_datetime

    # go through the user's accepted events
    if "events_accepted" in user and user["events_accepted"]:
        if isinstance(user["events_accepted"], dict):
            for event_id, event_datetime in user["events_accepted"].items():
                if event_datetime >= current_datetime:
                    user_event_datetimes[event_id] = event_datetime

    # we have to get all of the details for the events
    if user_event_datetimes:
        events_collection = get_db()["events"]
        # go through each event
        for event_id, event_datetime in user_event_datetimes.items():
            event = events_collection.find_one({"_id": ObjectId(event_id)})

            if event:
                upcoming_events.append({
                    "_id": event.get("_id"),
                    "name": event.get("name", "Untitled Event"),
                    "location": event.get("location", "No location specified"),
                    "date": event_datetime,
                    "details": event.get("description", "No description provided")
                })

    # we have to sort the events by the most recent first
    upcoming_events.sort(key=lambda x: x["date"])

    return render_template("home-upcoming.html", upcoming_events=upcoming_events)


@app.route("/invites")
@login_required
def invites():
    # get current user
    users_collection = get_users_collection()
    user = users_collection.find_one({"_id": ObjectId(current_user.id)})

    # get all of the invited events
    current_datetime = datetime.now()
    invited_events = []

    user_event_datetimes = {}

    # go through the user's upcoming invited events
    if "event_invites" in user and user["event_invites"]:
        if isinstance(user["event_invites"], dict):
            for event_id, event_datetime in user["event_invites"].items():
                if event_datetime >= current_datetime:
                    user_event_datetimes[event_id] = event_datetime

    # we have to get all of the details for the events
    if user_event_datetimes:
        events_collection = get_db()["events"]
        # go through each event
        for event_id, event_datetime in user_event_datetimes.items():
            event = events_collection.find_one({"_id": ObjectId(event_id)})

            if event:
                invited_events.append({
                    "_id": event.get("_id"),
                    "name": event.get("name", "Untitled Event"),
                    "location": event.get("location", "No location specified"),
                    "date": event_datetime,
                    "details": event.get("description", "No description provided")
                })

    # we have to sort the events by the most recent first
    invited_events.sort(key=lambda x: x["date"])

    return render_template("invites.html", invited_events=invited_events)


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