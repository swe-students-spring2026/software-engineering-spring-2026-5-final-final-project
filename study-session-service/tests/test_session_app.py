import importlib.util
import sys
from pathlib import Path

import mongomock
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("app", ROOT / "app.py")
study_session_app = importlib.util.module_from_spec(spec)
sys.modules["app"] = study_session_app
spec.loader.exec_module(study_session_app)
app = study_session_app.app


@pytest.fixture
def fake_db(monkeypatch):
    database = mongomock.MongoClient().studycast
    monkeypatch.setattr(study_session_app, "db", database)
    return database


def test_health():
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_index_is_health():
    response = app.test_client().get("/")
    assert response.status_code == 200
    assert response.get_json()["service"] == "study-session-service"


def test_detect():
    response = app.test_client().post("/detect", json={"looking_away": True})
    assert response.status_code == 200
    assert response.get_json()["status"] == "at-risk"


def test_create_and_end_session(fake_db):
    client = app.test_client()

    response = client.post("/sessions", json={"user": "Ada"})
    assert response.status_code == 201
    session_id = response.get_json()["session_id"]
    created = fake_db.study_sessions.find_one({"user": "Ada"})
    assert created is not None
    assert created["ended_at"] is None

    response = client.post(f"/sessions/{session_id}/end", json={"distraction_count": "3"})
    assert response.status_code == 200
    assert response.get_json() == {"distraction_count": 3, "status": "ended"}
    updated = fake_db.study_sessions.find_one({"_id": created["_id"]})
    assert updated["ended_at"] is not None
    assert updated["distraction_count"] == 3
