import importlib.util
import sys
from pathlib import Path
from urllib.error import URLError

import mongomock
import pytest
from bson.objectid import ObjectId
from pymongo.errors import PyMongoError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("app", ROOT / "app.py")
planner_web_app = importlib.util.module_from_spec(spec)
sys.modules["app"] = planner_web_app
spec.loader.exec_module(planner_web_app)
app = planner_web_app.app
app.template_folder = str(ROOT / "templates")
app.static_folder = str(ROOT / "static")


@pytest.fixture
def fake_db(monkeypatch):
    database = mongomock.MongoClient().studycast
    monkeypatch.setattr(planner_web_app, "db", database)
    return database


@pytest.fixture
def client(fake_db):
    app.config.update(TESTING=True, SECRET_KEY="test-secret")
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def rendered(monkeypatch):
    calls = []

    def fake_render(template, **context):
        calls.append((template, context))
        return f"rendered:{template}"

    monkeypatch.setattr(planner_web_app, "render_template", fake_render)
    return calls


def login(client, name="Tester"):
    with client.session_transaction() as flask_session:
        flask_session["user_name"] = name


def test_auth_signup_signin_logout_and_errors(client, fake_db, rendered):
    response = client.get("/auth")
    assert response.status_code == 200
    assert rendered[-1] == ("auth.html", {"error": None, "active_tab": "signin"})

    response = client.post(
        "/auth",
        data={
            "action": "signup",
            "name": "Ada",
            "email": "ada@example.com",
            "password": "pw",
        },
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/dashboard"
    assert fake_db.users.find_one({"email": "ada@example.com"})["name"] == "Ada"

    assert client.get("/auth").headers["Location"] == "/dashboard"
    assert client.get("/logout").headers["Location"] == "/auth"

    response = client.post(
        "/auth",
        data={
            "action": "signup",
            "name": "Ada",
            "email": "ada@example.com",
            "password": "pw",
        },
    )
    assert response.status_code == 200
    assert rendered[-1][1]["error"] == "User already exists."
    assert rendered[-1][1]["active_tab"] == "signup"

    response = client.post(
        "/auth",
        data={"action": "signin", "email": "ada@example.com", "password": "bad"},
    )
    assert response.status_code == 200
    assert rendered[-1][1]["error"] == "Invalid login."

    response = client.post(
        "/auth",
        data={"action": "signin", "email": "ada@example.com", "password": "pw"},
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/dashboard"


def test_auth_handles_database_failure(client, monkeypatch, rendered):
    class BrokenUsers:
        def find_one(self, query):
            raise PyMongoError("database down")

    class BrokenDb:
        users = BrokenUsers()

    monkeypatch.setattr(planner_web_app, "db", BrokenDb())

    response = client.post(
        "/auth",
        data={"action": "signin", "email": "ada@example.com", "password": "pw"},
    )
    assert response.status_code == 200
    assert "Database unavailable" in rendered[-1][1]["error"]
    assert rendered[-1][1]["active_tab"] == "signin"


def test_preparation_and_dashboard_helpers(fake_db):
    fake_db.preparations.insert_many([
        {"preparation_date": "2099-01-01", "difficulty": "Light (~1 hr)"},
        {"preparation_date": "2099-01-01", "difficulty": "Medium (~3 hrs)"},
        {"preparation_date": "2099-01-02", "difficulty": "Heavy (~5+ hrs)"},
    ])

    assert planner_web_app.get_preparation_hours("Light (~1 hr)") == 1
    assert planner_web_app.get_preparation_hours("Medium (~3 hrs)") == 3
    assert planner_web_app.get_preparation_hours("Heavy (~5+ hrs)") == 5
    assert planner_web_app.get_preparation_hours("Unknown") == 0
    assert planner_web_app.get_total_preparation_hours("2099-01-01") == 4

    exams = [{"_id": "a"}, {"_id": "b"}]
    color_map = planner_web_app.assign_dashboard_colors(exams)
    assert color_map["a"] == planner_web_app.DASHBOARD_COLORS[0]
    assert exams[1]["dashboard_color"] == planner_web_app.DASHBOARD_COLORS[1]


def test_dashboard_and_todo_routes(client, fake_db, rendered):
    login(client)
    today_id = fake_db.todos.insert_one({
        "task": "Read chapter",
        "type": "today",
        "completed": False,
    }).inserted_id
    long_term_id = fake_db.todos.insert_one({
        "task": "Plan project",
        "type": "long-term",
        "completed": False,
    }).inserted_id
    exam_id = fake_db.exams.insert_one({
        "subject": "Math",
        "exam_date": "2099-01-01",
        "exam_type": "Final",
        "status": "upcoming",
    }).inserted_id
    fake_db.exams.insert_one({
        "subject": "History",
        "exam_date": "2000-01-01",
        "exam_type": "Midterm",
        "status": "done",
    })
    fake_db.preparations.insert_one({
        "exam_id": exam_id,
        "preparation_date": "2099-01-02",
        "difficulty": "Light (~1 hr)",
        "location": "Library",
        "notes": "",
        "completed": False,
    })

    assert client.get("/").headers["Location"] == "/dashboard"
    response = client.get("/dashboard")
    assert response.status_code == 200
    dashboard_context = rendered[-1][1]
    assert len(dashboard_context["today_todos"]) == 1
    assert len(dashboard_context["long_term_todos"]) == 1
    assert len(dashboard_context["upcoming_exams"]) == 1
    assert len(dashboard_context["past_exams"]) == 1

    response = client.get("/todos")
    assert response.status_code == 200
    assert rendered[-1][0] == "todos.html"

    response = client.post("/add-todo", data={"task": "Draft tests", "type": "today"})
    assert response.headers["Location"] == "/todos"
    assert fake_db.todos.find_one({"task": "Draft tests"})

    response = client.post(f"/complete-todo/{today_id}")
    assert response.headers["Location"] == "/todos"
    assert fake_db.todos.find_one({"_id": today_id})["completed"] is True

    response = client.post(f"/delete-todo/{long_term_id}")
    assert response.headers["Location"] == "/todos"
    assert fake_db.todos.find_one({"_id": long_term_id}) is None


def test_exam_and_preparation_routes(client, fake_db, rendered):
    login(client)
    assert client.get("/exams").status_code == 200

    response = client.post(
        "/add-exam",
        data={"subject": "Chemistry", "exam_date": "2099-03-01", "exam_type": "Lab"},
    )
    assert response.headers["Location"] == "/exams"
    exam = fake_db.exams.find_one({"subject": "Chemistry"})
    exam_id = exam["_id"]

    response = client.get(f"/edit-exam/{exam_id}")
    assert response.status_code == 200
    assert rendered[-1][0] == "edit_exam.html"

    response = client.post(
        f"/edit-exam/{exam_id}",
        data={
            "subject": "Chemistry II",
            "exam_date": "2099-03-02",
            "exam_type": "Final",
            "status": "upcoming",
        },
    )
    assert response.headers["Location"] == "/exams"
    assert fake_db.exams.find_one({"_id": exam_id})["subject"] == "Chemistry II"

    missing_id = ObjectId()
    assert client.get(f"/edit-exam/{missing_id}").headers["Location"] == "/exams"

    response = client.get("/preparations")
    assert response.status_code == 200
    assert rendered[-1][0] == "preparations.html"

    response = client.post(
        "/add-preparation",
        data={
            "exam_id": str(exam_id),
            "preparation_date": "2099-03-03",
            "difficulty": "Medium (~3 hrs)",
            "location": "Library",
            "notes": "Practice problems",
        },
    )
    assert response.headers["Location"] == "/preparations"
    preparation = fake_db.preparations.find_one({"notes": "Practice problems"})
    preparation_id = preparation["_id"]

    for _ in range(4):
        fake_db.preparations.insert_one({
            "exam_id": exam_id,
            "preparation_date": "2099-04-01",
            "difficulty": "Heavy (~5+ hrs)",
            "location": "Library",
            "notes": "",
            "completed": False,
        })

    response = client.post(
        "/add-preparation",
        data={
            "exam_id": str(exam_id),
            "preparation_date": "2099-04-01",
            "difficulty": "Heavy (~5+ hrs)",
            "location": "Library",
            "notes": "",
        },
    )
    assert response.status_code == 200
    assert "already has 20 hours planned" in rendered[-1][1]["error"]

    response = client.post(
        f"/complete-preparation/{preparation_id}",
        data={"redirect_to": "/dashboard"},
    )
    assert response.headers["Location"] == "/dashboard"
    assert fake_db.preparations.find_one({"_id": preparation_id})["completed"] is True

    response = client.post(f"/delete-preparation/{preparation_id}")
    assert response.headers["Location"] == "/preparations"
    assert fake_db.preparations.find_one({"_id": preparation_id}) is None

    response = client.post(f"/complete-exam/{exam_id}", data={"redirect_to": "/dashboard"})
    assert response.headers["Location"] == "/dashboard"
    assert fake_db.exams.find_one({"_id": exam_id})["status"] == "done"

    fake_db.preparations.insert_one({"exam_id": exam_id, "preparation_date": "2099-05-01"})
    response = client.post(f"/delete-exam/{exam_id}")
    assert response.headers["Location"] == "/exams"
    assert fake_db.exams.find_one({"_id": exam_id}) is None
    assert fake_db.preparations.find_one({"exam_id": exam_id}) is None


def test_study_session_routes_success(client, monkeypatch, rendered):
    login(client, "Ada")
    calls = []

    def fake_service(path, method="GET", payload=None):
        calls.append((path, method, payload))
        return {"path": path, "method": method, "payload": payload}

    monkeypatch.setattr(planner_web_app, "call_study_session_service", fake_service)

    response = client.get("/study-sessions")
    assert response.status_code == 200
    assert rendered[-1][1]["service_status"]["path"] == "/health"

    response = client.post("/study-sessions/start")
    assert response.headers["Location"] == "/study-sessions"
    assert calls[-1] == ("/sessions", "POST", {"user": "Ada"})

    response = client.post("/study-sessions/start-json")
    assert response.status_code == 200
    assert response.get_json()["payload"] == {"user": "Ada"}

    response = client.post("/study-sessions/end-json", json={})
    assert response.status_code == 400

    response = client.post(
        "/study-sessions/end-json",
        json={"session_id": "abc123", "distraction_count": "2"},
    )
    assert response.status_code == 200
    assert calls[-1] == ("/sessions/abc123/end", "POST", {"distraction_count": 2})

    response = client.post(
        "/study-sessions/detect",
        data={"face_present": "true", "looking_away": "true", "phone_visible": "true"},
    )
    assert response.headers["Location"] == "/study-sessions"
    assert calls[-1][2] == {
        "face_present": True,
        "looking_away": True,
        "phone_visible": True,
    }

    response = client.post(
        "/study-sessions/detect-json",
        json={"face_present": False, "looking_away": True, "phone_visible": True},
    )
    assert response.status_code == 200
    assert calls[-1][2] == {
        "face_present": False,
        "looking_away": True,
        "phone_visible": False,
    }


def test_study_session_routes_handle_service_failure(client, monkeypatch, rendered):
    login(client)

    def broken_service(*args, **kwargs):
        raise URLError("offline")

    monkeypatch.setattr(planner_web_app, "call_study_session_service", broken_service)

    response = client.get("/study-sessions")
    assert response.status_code == 200
    assert rendered[-1][1]["service_error"] == "Study session service is unavailable."

    response = client.post("/study-sessions/start")
    assert response.headers["Location"] == "/study-sessions"
    with client.session_transaction() as flask_session:
        assert flask_session["study_session_result"] == {"error": "Could not start session."}

    assert client.post("/study-sessions/start-json").status_code == 503
    assert client.post(
        "/study-sessions/end-json",
        json={"session_id": "abc123"},
    ).status_code == 503

    response = client.post("/study-sessions/detect", data={})
    assert response.headers["Location"] == "/study-sessions"
    with client.session_transaction() as flask_session:
        assert flask_session["study_detection_result"] == {"error": "Could not analyze focus."}

    assert client.post("/study-sessions/detect-json", json={}).status_code == 503
