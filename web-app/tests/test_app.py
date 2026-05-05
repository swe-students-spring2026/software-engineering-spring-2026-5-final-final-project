import pytest
from unittest.mock import patch, MagicMock
from bson.objectid import ObjectId

with patch('config.Config.connect_to_db', return_value=MagicMock()):
    from app import app, User
import json


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_data():
    return {
        "title": "Final Project",
        "course": "Software Engineering",
        "description": "Finish Docker and CI/CD",
        "due_date": "2026-05-05",
        "date": "2026-05-05",
    }


@pytest.fixture
def login_test_user(client):
    with client.session_transaction() as session:
        session["_user_id"] = "test@example.com"
        session["_fresh"] = True
    yield session


def test_user_loader():
    from app import user_loader

    with patch("app.mongo") as mock_mongo:
        mock_mongo.users.find_one.return_value = {
            "user_email": "test@example.com",
        }
        user = user_loader("test@example.com")

        assert isinstance(user, User)
        assert user.id == "test@example.com"


def test_request_loader():
    from app import request_loader

    with patch("app.mongo") as mock_mongo:
        mock_mongo.users.find_one.return_value = {
            "user_email": "test@example.com",
        }
        user = request_loader(
            request=type(
                "Request", (object,), {"form": {"username": "test@example.com"}}
            )
        )

        assert isinstance(user, User)
        assert user.id == "test@example.com"


def test_add_id():
    from app import add_id

    test_id = ObjectId()
    tasks = [{"_id": test_id}, {"_id": "def456"}]
    result = add_id(tasks)
    assert result[0]["id"] == str(test_id)
    assert result[1]["id"] == "def456"


def test_compute_status():
    from app import compute_status
    from datetime import datetime, timedelta

    past = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    due_soon = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    upcoming = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    assert compute_status(past) == "overdue"
    assert compute_status(due_soon) == "due_soon"
    assert compute_status(upcoming) == "upcoming"


def test_index_route(client, login_test_user):
    with patch("app.mongo") as mock_mongo:
        mock_mongo.assignments.find.side_effect = [
            [
                {
                    "_id": ObjectId(),
                    "title": "Overdue Assignment",
                    "course": "Test Course",
                    "user_email": "test@example.com",
                    "due_date": "2020-01-01",
                    "status": "overdue",
                },
                {
                    "_id": ObjectId(),
                    "title": "Due_Soon Assignment",
                    "course": "Test Course",
                    "user_email": "test@example.com",
                    "due_date": "2026-05-05",
                    "status": "due_soon",
                },
                {
                    "_id": ObjectId(),
                    "title": "Upcoming Assignment",
                    "course": "Test Course",
                    "user_email": "test@example.com",
                    "due_date": "2026-10-01",
                    "status": "upcoming",
                },
            ],
            [],
        ]
        response = client.get("/")

    assert response.status_code == 200
    assert b"Overdue Assignment" in response.data
    assert b"Due_Soon Assignment" in response.data
    assert b"Upcoming Assignment" in response.data


def test_submit_new_task_route_failure(client, login_test_user, sample_data):
    with patch("app.requests.post") as mock_ml_request:
        with patch("app.mongo"):
            mock_ml_request.side_effect = Exception("ML service error")
            response = client.post("/submit_new_task", json=sample_data)

    data = json.loads(response.data)
    assert data["status"] == "error"
    assert "Failed to analyze assignment" in data["message"]


def test_submit_new_task_route_success(client, login_test_user, sample_data):
    with patch("app.requests.post") as mock_ml_request:
        with patch("app.mongo"):
            mock_ml_request.return_value.json.return_value = {
                "estimated_hours": 5,
                "difficulty": "medium",
                "priority": "high",
            }
            response = client.post("/submit_new_task", json=sample_data)

    data = json.loads(response.data)
    assert data["status"] == "success"
    assert response.status_code == 200


def test_login_success(client):
    with patch("app.mongo") as mock_mongo:
        mock_mongo.users.find_one.return_value = {
            "user_email": "test@example.com",
            "password": "testpassword",
        }
        response = client.post(
            "/api/auth/login",
            data={"username": "test@example.com", "password": "testpassword"},
        )
    assert response.status_code == 302


def test_login_failure(client):
    with patch("app.mongo") as mock_mongo:
        mock_mongo.users.find_one.return_value = None
        response = client.post(
            "/api/auth/login",
            data={"username": "test@example.com", "password": "testpassword"},
        )
    assert response.status_code != 302


def test_register_success(client):
    with patch("app.mongo") as mock_mongo:
        mock_mongo.users.find_one.return_value = None
        response = client.post(
            "/api/auth/register",
            data={"username": "test@example.com", "password": "testpassword"},
        )
    assert response.status_code == 302


def test_register_failure(client):
    with patch("app.mongo") as mock_mongo:
        mock_mongo.users.find_one.return_value = {
            "user_email": "test@example.com",
            "password": "testpassword",
        }
        response = client.post(
            "/api/auth/register",
            data={"username": "test@example.com", "password": "testpassword"},
        )
    assert response.status_code != 302


def test_edit_task_post_route(client, login_test_user, sample_data):
    with patch("app.mongo") as mock_mongo:
        with patch("app.ObjectId") as mock_object_id:
            mock_object_id.return_value = ObjectId("123456789012345678901234")
        mock_mongo.assignments.find_one.return_value = sample_data
        response = client.post(
            "/task/123456789012345678901234/edit",
            data={
                "title": "Test Task",
                "course": "Test Course",
                "description": "Test Description",
                "due_date": "2026-05-05",
            },
        )
    assert response.status_code == 302
    assert "/task" in response.headers["Location"]


def test_complete_task_route(client):
    with patch("app.mongo") as mock_mongo:
        with patch("app.ObjectId") as mock_object_id:
            mock_object_id.return_value = ObjectId("123456789012345678901234")
        mock_mongo.assignments.find_one.return_value = {}
        response = client.get("/complete_task/123456789012345678901234")

    assert response.status_code == 302
    assert "/" in response.headers["Location"]
