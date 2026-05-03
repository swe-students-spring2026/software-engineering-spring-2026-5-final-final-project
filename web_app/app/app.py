import os

from bson.errors import InvalidId
from bson import ObjectId
from flask import Flask, redirect, render_template, request, url_for
from datetime import datetime, timedelta
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
import requests


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


#microservice for invite-adjuster
def get_lateness_penalty(user_id):
    try:
        res = requests.get(f"http://invite-adjuster:5000/lateness_penalty/{user_id}")
        data = res.json()
        return data.get("lateness_penalty", 0) or 0
    except Exception as e:
        print("Error calling invite-adjuster:", e)
        return 0
    
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
    if date is None:
        return "No time set"
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
                invitee_info = None

                for invitee in event.get("invitees_list", []):
                    if invitee.get("user_id") == current_user.id:
                        invitee_info = invitee
                        break
                
                display_time = event_datetime

                if invitee_info and invitee_info.get("suggested_arrival_time"):
                    display_time = invitee_info["suggested_arrival_time"]

                invited_events.append({
                    "_id": event.get("_id"),
                    "name": event.get("name", "Untitled Event"),
                    "location": event.get("location", "No location specified"),
                    "date": display_time,
                    "details": event.get("description", "No description provided")
                })

    # we have to sort the events by the most recent first
    invited_events.sort(key=lambda x: x["date"])

    return render_template("invites.html", invited_events=invited_events)

# a user accepts an event
@app.route("/invites/<event_id>/accept", methods=["GET", "POST"])
@login_required
def accept_event(event_id):
    user_id = current_user.get_id()
    db = get_db()
    users = db["users"]
    events = db["events"]
    
    # check if event exists
    event = events.find_one({"_id": ObjectId(event_id)})
    if not event:
        return redirect(url_for("invites"))
    
    # delete event from user's invites
    users.update_one(
        {"_id": ObjectId(user_id)},
        {"$unset": {f"event_invites.{event_id}": ""}}
    )

    # get the user's time for the event
    invitee = next(
        (inv for inv in event.get("invitees_list", []) if inv.get("user_id") == user_id),
        None
    )

    suggested_arrival_time = invitee.get("suggested_arrival_time")

    # add to user's events
    users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {f"events_accepted.{event_id}": suggested_arrival_time}}
    )

    # mark user as accepted in event
    events.update_one(
        {"_id": ObjectId(event_id), "invitees_list.user_id": user_id},
        {"$set": {"invitees_list.$.status": "accepted"}}
    )
    
    return redirect(url_for("invites"))

# user declines an event
@app.route("/invites/<event_id>/decline", methods=["GET", "POST"])
@login_required
def decline_event(event_id):
    user_id = current_user.get_id()
    db = get_db()
    users = db["users"]
    events = db["events"]
    
    # check if event exists
    event = events.find_one({"_id": ObjectId(event_id)})
    if not event:
        return redirect(url_for("invites"))
    
    # delete event from user's invites
    users.update_one(
        {"_id": ObjectId(user_id)},
        {"$unset": {f"event_invites.{event_id}": ""}}
    )

    # mark user as declined in event
    events.update_one(
        {"_id": ObjectId(event_id), "invitees_list.user_id": user_id},
        {"$set": {"invitees_list.$.status": "declined"}}
    )
    
    return redirect(url_for("invites"))

@app.route("/host-events")
@login_required
def host_events():
    users = get_users_collection()
    events = get_db()["events"]
    user = users.find_one({"_id": ObjectId(current_user.id)})
    hosting_events = []
    for event_id, event_datetime in user.get("events_owned", {}).items():
        event = events.find_one({"_id": ObjectId(event_id)})
        if event:
            hosting_events.append({
                "_id": event["_id"],
                "name": event.get("name", "Untitled Event"),
                "location": event.get("location", "No location specified"),
                "date": event_datetime,
                "details": event.get("description", "No description provided"),
                "invitees_list": event.get("invitees_list", [])
            })
    return render_template("host-events.html", hosting_events=hosting_events)

@app.route("/host-events/create", methods=["GET", "POST"])
@login_required
def create_host_event():
    users = get_users_collection()
    events = get_db()["events"]

    error = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        location = request.form.get("location", "").strip()
        date = request.form.get("date", "").strip()
        time = request.form.get("time", "").strip()
        details = request.form.get("details", "").strip()

        invitee_usernames = request.form.getlist("invitee_username")

        if not name or not location or not date or not time:
            error = "Please fill in name, location, date, and time."
            return render_template("host-event-create.html", error=error)

        try:
            event_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        except ValueError:
            error = "Invalid date or time."
            return render_template("host-event-create.html", error=error)

        invitees_list = []

        for username in invitee_usernames:
            username = username.strip()

            if not username:
                continue

            invitee_user = users.find_one({"name": username})
            

            if not invitee_user:
                print(f"Invitee not found: {username}")
                continue

            lateness_penalty = get_lateness_penalty(str(invitee_user["_id"]))
            lateness_penalty = max(lateness_penalty, 0)
            suggested_arrival = event_datetime - timedelta(minutes=lateness_penalty)

            invitees_list.append({
                "user_id": str(invitee_user["_id"]),
                "name": invitee_user["name"],
                "time": time,
                "suggested_arrival_time": suggested_arrival,
                "lateness_penalty": lateness_penalty,
                "status": "pending"
            })

        event_doc = {
            "name": name,
            "location": location,
            "date": event_datetime,
            "description": details,
            "host_id": current_user.id,
            "invitees_list": invitees_list,
            "created_at": datetime.now()
        }

        result = events.insert_one(event_doc)
        event_id = str(result.inserted_id)

        users.update_one(
            {"_id": ObjectId(current_user.id)},
            {"$set": {f"events_owned.{event_id}": event_datetime}}
        )

        for invitee in invitees_list:
            users.update_one(
                {"_id": ObjectId(invitee["user_id"])},
                {"$set": {f"event_invites.{event_id}": event_datetime}}
            )

        return redirect(url_for("host_events"))

    return render_template("host-event-create.html", error=error)

@app.route("/host-events/<event_id>/edit", methods=["GET", "POST"])
@login_required
def edit_host_event(event_id):
    users = get_users_collection()
    events = get_db()["events"]

    event = events.find_one({
        "_id": ObjectId(event_id),
        "host_id": current_user.id
    })

    if not event:
        return redirect(url_for("host_events"))

    error = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        location = request.form.get("location", "").strip()
        date = request.form.get("date", "").strip()
        time = request.form.get("time", "").strip()
        details = request.form.get("details", "").strip()
        invitee_usernames = request.form.getlist("invitee_username")

        try:
            event_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        except ValueError:
            error = "Invalid date or time."
            return render_template("host-event-edit.html", event=event, error=error)

        old_invitees = event.get("invitees_list", [])
        old_invitee_ids = [invitee["user_id"] for invitee in old_invitees]

        new_invitees_list = []
        new_invitee_ids = []

        for username in invitee_usernames:
            username = username.strip()

            if not username:
                continue

            invitee_user = users.find_one({"name": username})

            if not invitee_user:
                print(f"Invitee not found: {username}")
                continue

            invitee_id = str(invitee_user["_id"])
            new_invitee_ids.append(invitee_id)

            lateness_penalty = max(get_lateness_penalty(invitee_user), 0)
            suggested_arrival = event_datetime - timedelta(minutes=lateness_penalty)

            new_invitees_list.append({
                "user_id": invitee_id,
                "name": invitee_user["name"],
                "time": time,
                "suggested_arrival_time": suggested_arrival,
                "lateness_penalty": lateness_penalty,
                "status": "pending"
            })

        events.update_one(
            {"_id": ObjectId(event_id)},
            {
                "$set": {
                    "name": name,
                    "location": location,
                    "date": event_datetime,
                    "description": details,
                    "invitees_list": new_invitees_list,
                    "updated_at": datetime.now()
                }
            }
        )

        users.update_one(
            {"_id": ObjectId(current_user.id)},
            {"$set": {f"events_owned.{event_id}": event_datetime}}
        )

        for invitee_id in old_invitee_ids:
            users.update_one(
                {"_id": ObjectId(invitee_id)},
                {"$unset": {f"event_invites.{event_id}": ""}}
            )

        for invitee_id in new_invitee_ids:
            users.update_one(
                {"_id": ObjectId(invitee_id)},
                {"$set": {f"event_invites.{event_id}": event_datetime}}
            )

        return redirect(url_for("host_events"))

    return render_template("host-event-edit.html", event=event, error=error)     

@app.route("/host-events/<event_id>/delete", methods=["POST"])
@login_required
def delete_host_event(event_id):
    users = get_users_collection()
    events = get_db()["events"]

    event = events.find_one({
        "_id": ObjectId(event_id),
        "host_id": current_user.id
    })

    if not event:
        return redirect(url_for("host_events"))

    invitees = event.get("invitees_list", [])

    for invitee in invitees:
        users.update_one(
            {"_id": ObjectId(invitee["user_id"])},
            {"$unset": {f"event_invites.{event_id}": ""}}
        )

    users.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$unset": {f"events_owned.{event_id}": ""}}
    )

    events.delete_one({"_id": ObjectId(event_id)})

    return redirect(url_for("host_events"))

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
    app.run(host="0.0.0.0", port=5000, debug=True)