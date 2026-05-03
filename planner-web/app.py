from flask import Flask, request, render_template, redirect, session, jsonify
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from dotenv import load_dotenv
import os
import json
from bson.objectid import ObjectId
from functools import wraps
from datetime import date
from urllib.error import URLError
from urllib.request import Request as UrlRequest, urlopen

from calendar_weather import register_calendar_weather_routes




load_dotenv()

app = Flask(__name__)
app.secret_key = "studycast-secret-key"
client = MongoClient(
    os.getenv("MONGO_URI", "mongodb://localhost:27017/"),
    serverSelectionTimeoutMS=2000,
    connectTimeoutMS=2000
)
db = client["studycast"]
study_session_service_url = os.getenv(
    "STUDY_SESSION_SERVICE_URL",
    "http://localhost:5002"
).rstrip("/")


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if "user_name" not in session:
            return redirect("/auth")
        return view_func(*args, **kwargs)

    return wrapped_view


register_calendar_weather_routes(app, db, login_required)


def call_study_session_service(path, method="GET", payload=None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request_obj = UrlRequest(
        f"{study_session_service_url}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    with urlopen(request_obj, timeout=3) as response:
        return json.load(response)


def render_auth_page(error=None, active_tab="signin"):
    return render_template("auth.html", error=error, active_tab=active_tab)


@app.route("/study-sessions", methods=["GET"])
@login_required
def study_sessions_page():
    service_status = None
    service_error = None
    detection_result = session.pop("study_detection_result", None)
    session_result = session.pop("study_session_result", None)

    try:
        service_status = call_study_session_service("/health")
    except (OSError, URLError, TimeoutError):
        service_error = "Study session service is unavailable."

    return render_template(
        "study_sessions.html",
        service_status=service_status,
        service_error=service_error,
        detection_result=detection_result,
        session_result=session_result,
    )


@app.route("/study-sessions/start", methods=["POST"])
@login_required
def start_study_session():
    try:
        session["study_session_result"] = call_study_session_service(
            "/sessions",
            method="POST",
            payload={"user": session.get("user_name", "anonymous")},
        )
    except (OSError, URLError, TimeoutError):
        session["study_session_result"] = {"error": "Could not start session."}
    return redirect("/study-sessions")


@app.route("/study-sessions/start-json", methods=["POST"])
@login_required
def start_study_session_json():
    try:
        return jsonify(call_study_session_service(
            "/sessions",
            method="POST",
            payload={"user": session.get("user_name", "anonymous")},
        ))
    except (OSError, URLError, TimeoutError):
        return jsonify({"error": "Could not start session."}), 503


@app.route("/study-sessions/end-json", methods=["POST"])
@login_required
def end_study_session_json():
    payload = request.get_json(silent=True) or {}
    session_id = payload.get("session_id")
    if not session_id:
        return jsonify({"error": "Missing session id."}), 400
    try:
        return jsonify(call_study_session_service(
            f"/sessions/{session_id}/end",
            method="POST",
            payload={"distraction_count": int(payload.get("distraction_count", 0))},
        ))
    except (OSError, URLError, TimeoutError):
        return jsonify({"error": "Could not end session."}), 503


@app.route("/study-sessions/detect", methods=["POST"])
@login_required
def detect_study_distraction():
    payload = {
        "face_present": request.form.get("face_present") == "true",
        "looking_away": request.form.get("looking_away") == "true",
        "phone_visible": request.form.get("phone_visible") == "true",
    }
    try:
        session["study_detection_result"] = call_study_session_service(
            "/detect",
            method="POST",
            payload=payload,
        )
    except (OSError, URLError, TimeoutError):
        session["study_detection_result"] = {"error": "Could not analyze focus."}
    return redirect("/study-sessions")


@app.route("/study-sessions/detect-json", methods=["POST"])
@login_required
def detect_study_distraction_json():
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(call_study_session_service(
            "/detect",
            method="POST",
            payload={
                "face_present": bool(payload.get("face_present", True)),
                "looking_away": bool(payload.get("looking_away", False)),
                "phone_visible": False,
            },
        ))
    except (OSError, URLError, TimeoutError):
        return jsonify({"error": "Could not analyze focus."}), 503


PREPARATION_HOURS = {
    "Light (~1 hr)": 1,
    "Medium (~3 hrs)": 3,
    "Heavy (~5+ hrs)": 5
}

DASHBOARD_COLORS = [
    "#2563eb",
    "#dc2626",
    "#16a34a",
    "#ea580c",
    "#7c3aed",
    "#0891b2",
    "#c2410c",
    "#be185d"
]


def get_preparation_hours(difficulty):
    return PREPARATION_HOURS.get(difficulty, 0)


def get_total_preparation_hours(preparation_date):
    total_hours = 0
    preparations = db.preparations.find({"preparation_date": preparation_date}, {"difficulty": 1})
    for preparation in preparations:
        total_hours += get_preparation_hours(preparation.get("difficulty"))
    return total_hours


def render_preparations_page(error=None):
    exams = list(db.exams.find().sort("exam_date", 1))
    preparations = list(db.preparations.find().sort("preparation_date", 1))

    exam_lookup = {}
    for exam in exams:
        exam["_id"] = str(exam["_id"])
        exam_lookup[exam["_id"]] = exam

    for preparation in preparations:
        preparation["_id"] = str(preparation["_id"])
        preparation["exam_id"] = str(preparation["exam_id"])
        preparation["exam"] = exam_lookup.get(preparation["exam_id"])
        preparation["completed"] = preparation.get("completed", False)

    return render_template(
        "preparations.html",
        exams=exams,
        preparations=preparations,
        error=error
    )


def assign_dashboard_colors(exams):
    color_map = {}
    for index, exam in enumerate(exams):
        color_map[exam["_id"]] = DASHBOARD_COLORS[index % len(DASHBOARD_COLORS)]
        exam["dashboard_color"] = color_map[exam["_id"]]
    return color_map

@app.route("/")
def home():
    if "user_name" in session:
        return redirect("/dashboard")
    return redirect("/auth")


@app.route("/dashboard")
@login_required
def dashboard():
    today = date.today()
    todos = list(db.todos.find())
    exams = list(db.exams.find().sort("exam_date", 1))
    preparations = list(db.preparations.find().sort("preparation_date", 1))

    today_todos = []
    long_term_todos = []
    upcoming_exams = []
    past_exams = []
    upcoming_preparations = []
    past_preparations = []

    for todo in todos:
        todo["_id"] = str(todo["_id"])

        if todo.get("type") == "today":
            today_todos.append(todo)
        else:
            long_term_todos.append(todo)

    exam_lookup = {}
    for exam in exams:
        exam["_id"] = str(exam["_id"])
        exam_lookup[exam["_id"]] = exam

        exam_day = date.fromisoformat(exam["exam_date"])
        if exam_day < today or exam.get("status") == "done":
            past_exams.append(exam)
        else:
            upcoming_exams.append(exam)

    exam_color_map = assign_dashboard_colors(exams)

    for preparation in preparations:
        preparation["_id"] = str(preparation["_id"])
        preparation["exam_id"] = str(preparation["exam_id"])
        preparation["exam"] = exam_lookup.get(preparation["exam_id"])
        preparation["completed"] = preparation.get("completed", False)
        preparation["dashboard_color"] = exam_color_map.get(preparation["exam_id"], "#6b7280")

        preparation_day = date.fromisoformat(preparation["preparation_date"])
        if preparation_day < today or preparation["completed"]:
            past_preparations.append(preparation)
        else:
            upcoming_preparations.append(preparation)

    return render_template(
        "dashboard.html",
        today_todos=today_todos,
        long_term_todos=long_term_todos,
        upcoming_exams=upcoming_exams,
        past_exams=past_exams,
        upcoming_preparations=upcoming_preparations,
        past_preparations=past_preparations
    )


@app.route("/todos")
@login_required
def todos_page():
    todos = list(db.todos.find())

    today_todos = []
    long_term_todos = []

    for todo in todos:
        todo["_id"] = str(todo["_id"])

        if todo.get("type") == "today":
            today_todos.append(todo)
        else:
            long_term_todos.append(todo)

    return render_template(
        "todos.html",
        today_todos=today_todos,
        long_term_todos=long_term_todos
    )


@app.route("/add-todo", methods=["POST"])
@login_required
def add_todo():
    task = request.form.get("task")
    todo_type = request.form.get("type")

    if task and todo_type:
        db.todos.insert_one({
            "task": task,
            "type": todo_type,
            "completed": False
        })

    return redirect("/todos")


@app.route("/complete-todo/<todo_id>", methods=["POST"])
@login_required
def complete_todo(todo_id):
    db.todos.update_one(
        {"_id": ObjectId(todo_id)},
        {"$set": {"completed": True}}
    )
    return redirect("/todos")


@app.route("/delete-todo/<todo_id>", methods=["POST"])
@login_required
def delete_todo(todo_id):
    db.todos.delete_one({"_id": ObjectId(todo_id)})
    return redirect("/todos")


@app.route("/exams")
@login_required
def exams_page():
    exams = list(db.exams.find())

    for exam in exams:
        exam["_id"] = str(exam["_id"])

    return render_template("exams.html", exams=exams)


@app.route("/preparations")
@login_required
def preparations_page():
    return render_preparations_page()


@app.route("/add-exam", methods=["POST"])
@login_required
def add_exam():
    subject = request.form.get("subject")
    exam_date = request.form.get("exam_date")
    exam_type = request.form.get("exam_type")

    if subject and exam_date and exam_type:
        db.exams.insert_one({
            "subject": subject,
            "exam_date": exam_date,
            "exam_type": exam_type,
            "status": "upcoming"
        })

    return redirect("/exams")


@app.route("/add-preparation", methods=["POST"])
@login_required
def add_preparation():
    exam_id = request.form.get("exam_id")
    preparation_date = request.form.get("preparation_date")
    difficulty = request.form.get("difficulty")
    location = request.form.get("location")
    notes = request.form.get("notes")

    if exam_id and preparation_date and difficulty and location:
        current_hours = get_total_preparation_hours(preparation_date)
        added_hours = get_preparation_hours(difficulty)

        if current_hours + added_hours >= 24:
            return render_preparations_page(
                f"That day already has {current_hours} hours planned. Add less than {24 - current_hours} more hours to stay under 24."
            )

        db.preparations.insert_one({
            "exam_id": ObjectId(exam_id),
            "preparation_date": preparation_date,
            "difficulty": difficulty,
            "location": location,
            "notes": notes,
            "completed": False
        })

    return redirect("/preparations")


@app.route("/delete-preparation/<preparation_id>", methods=["POST"])
@login_required
def delete_preparation(preparation_id):
    db.preparations.delete_one({"_id": ObjectId(preparation_id)})
    redirect_to = request.form.get("redirect_to")
    if redirect_to:
        return redirect(redirect_to)
    return redirect("/preparations")


@app.route("/complete-preparation/<preparation_id>", methods=["POST"])
@login_required
def complete_preparation(preparation_id):
    db.preparations.update_one(
        {"_id": ObjectId(preparation_id)},
        {"$set": {"completed": True}}
    )
    redirect_to = request.form.get("redirect_to")
    if redirect_to:
        return redirect(redirect_to)
    return redirect("/preparations")


@app.route("/complete-exam/<exam_id>", methods=["POST"])
@login_required
def complete_exam(exam_id):
    db.exams.update_one(
        {"_id": ObjectId(exam_id)},
        {"$set": {"status": "done"}}
    )
    redirect_to = request.form.get("redirect_to")
    if redirect_to:
        return redirect(redirect_to)
    return redirect("/exams")


@app.route("/edit-exam/<exam_id>", methods=["GET", "POST"])
@login_required
def edit_exam(exam_id):
    if request.method == "POST":
        db.exams.update_one(
            {"_id": ObjectId(exam_id)},
            {"$set": {
                "subject": request.form.get("subject"),
                "exam_date": request.form.get("exam_date"),
                "exam_type": request.form.get("exam_type"),
                "status": request.form.get("status")
            }}
        )
        return redirect("/exams")

    exam = db.exams.find_one({"_id": ObjectId(exam_id)})

    if not exam:
        return redirect("/exams")

    exam["_id"] = str(exam["_id"])
    return render_template("edit_exam.html", exam=exam)


@app.route("/delete-exam/<exam_id>", methods=["POST"])
@login_required
def delete_exam(exam_id):
    db.preparations.delete_many({"exam_id": ObjectId(exam_id)})
    db.exams.delete_one({"_id": ObjectId(exam_id)})
    return redirect("/exams")


@app.route("/auth", methods=["GET", "POST"])
def auth():
    if request.method == "GET" and "user_name" in session:
        return redirect("/dashboard")

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        action = request.form.get("action")  # login or signup

        try:
            if action == "signup":
                existing_user = db.users.find_one({"email": email})

                if existing_user:
                    return render_auth_page("User already exists.", active_tab="signup")

                db.users.insert_one({
                    "name": name,
                    "email": email,
                    "password": password
                })

                session["user_name"] = name
                return redirect("/dashboard")

            if action == "signin":
                user = db.users.find_one({
                    "email": email,
                    "password": password
                })

                if user:
                    session["user_name"] = user["name"]
                    return redirect("/dashboard")

                return render_auth_page("Invalid login.", active_tab="signin")
        except PyMongoError:
            return render_auth_page(
                "Database unavailable. Start MongoDB or set MONGO_URI, then try again.",
                active_tab="signup" if action == "signup" else "signin"
            )

    return render_auth_page()

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/auth")








if __name__ == "__main__":
    app.run(debug=True, port=5001)
