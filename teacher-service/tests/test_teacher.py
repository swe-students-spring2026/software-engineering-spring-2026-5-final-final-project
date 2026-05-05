"""Tests for the CatCh teacher-service FastAPI app."""

import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "main.py"
spec = importlib.util.spec_from_file_location("teacher_service_main", MODULE_PATH)
teacher_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teacher_main)

REPOSITORY_PATH = Path(__file__).resolve().parents[1] / "app" / "repository.py"
repo_spec = importlib.util.spec_from_file_location(
    "teacher_repository", REPOSITORY_PATH
)
teacher_repository = importlib.util.module_from_spec(repo_spec)
repo_spec.loader.exec_module(teacher_repository)

client = TestClient(teacher_main.app)


def test_health():
    """Health endpoint returns an ok status."""

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_teacher_rules_exclude_tokens():
    """Teacher rules keep cat users outside the token system."""

    response = client.get("/teacher/rules")
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "cat"
    assert body["token_system_enabled"] is False


def test_repository_token_policy_and_problem_limit():
    """Repository helper contracts match teacher token rules."""

    policy = teacher_repository.teacher_token_policy()
    assert policy["role"] == "cat"
    assert policy["token_system_enabled"] is False
    assert teacher_repository.validate_problem_count(["p1", "p2"]) is True
    assert (
        teacher_repository.validate_problem_count(
            [f"problem-{index}" for index in range(101)]
        )
        is False
    )


def test_create_private_pond_forwards_to_game_service(monkeypatch):
    """Creating a private fish pond forwards the expected cat payload."""

    calls = []

    async def fake_forward(method, path, payload=None):
        calls.append((method, path, payload))
        return {"pond_id": "pond-forwarded"}

    monkeypatch.setattr(teacher_main, "forward_to_game_service", fake_forward)
    response = client.post(
        "/teacher/ponds",
        json={
            "cat_id": "cat-1",
            "name": "Algorithms",
            "description": "practice",
            "visibility": "private",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pond_id"] == "pond-forwarded"
    assert body["visibility"] == "private"
    assert len(body["room_code"]) == 6
    assert calls[0][0] == "POST"
    assert calls[0][1] == "/ponds"
    assert calls[0][2]["created_by_role"] == "cat"
    assert calls[0][2]["token_cost"] == 0


def test_create_pond_falls_back_when_game_service_unavailable(monkeypatch):
    """The template contract still returns a pond when game-service is offline."""

    async def fake_forward(method, path, payload=None):
        raise teacher_main.HTTPException(status_code=502, detail="offline")

    monkeypatch.setattr(teacher_main, "forward_to_game_service", fake_forward)
    response = client.post(
        "/teacher/ponds",
        json={"cat_id": "cat-1", "name": "Fallback Pond", "visibility": "public"},
    )

    assert response.status_code == 200
    assert response.json()["pond_id"] == "pond_fallback_pond"
    assert response.json()["token_cost"] == 0


def test_list_teacher_ponds_falls_back_to_empty(monkeypatch):
    """Unavailable game-service list endpoints fall back to an empty list."""

    async def fake_forward(method, path, payload=None):
        raise teacher_main.HTTPException(status_code=404, detail="not ready")

    monkeypatch.setattr(teacher_main, "forward_to_game_service", fake_forward)
    assert client.get("/teacher/cat-1/ponds").json() == []
    assert client.get("/teacher/ponds/pond-1/problems").json() == []


def test_add_problem_validates_pond_id_and_falls_back(monkeypatch):
    """Adding a problem validates pond identity and produces a template response."""

    problem = {
        "cat_id": "cat-1",
        "pond_id": "pond-1",
        "title": "Return larger",
        "prompt": "Return the larger value.",
        "starter_code": "def larger(a, b):\n    pass\n",
        "reference_solution": "def larger(a, b):\n    return max(a, b)\n",
        "test_code": "import unittest\n",
        "topic": "conditionals",
    }
    mismatch = client.post("/teacher/ponds/other/problems", json=problem)
    assert mismatch.status_code == 400

    async def fake_forward(method, path, payload=None):
        raise teacher_main.HTTPException(status_code=502, detail="offline")

    monkeypatch.setattr(teacher_main, "forward_to_game_service", fake_forward)
    response = client.post("/teacher/ponds/pond-1/problems", json=problem)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued_template"
    assert body["problem"]["fishing_reward"] == 1
    assert body["problem"]["cat_token_reward"] == 0


def test_update_delete_and_assignment_forward(monkeypatch):
    """Problem editing, deletion, and assignment endpoints forward payloads."""

    calls = []

    async def fake_forward(method, path, payload=None):
        calls.append((method, path, payload))
        return {"ok": True, "path": path}

    monkeypatch.setattr(teacher_main, "forward_to_game_service", fake_forward)
    problem_update = {
        "cat_id": "cat-1",
        "title": "Edited",
        "prompt": "prompt",
        "starter_code": "",
        "reference_solution": "solution",
        "test_code": "tests",
        "topic": "arrays",
    }
    update = client.put("/teacher/ponds/pond-1/problems/problem-1", json=problem_update)
    assert update.status_code == 200

    delete = client.delete(
        "/teacher/ponds/pond-1/problems/problem-1",
        params={"cat_id": "cat 1"},
    )
    assert delete.status_code == 200

    assignment = client.post(
        "/teacher/ponds/pond-1/assignments",
        json={
            "cat_id": "cat-1",
            "pond_id": "pond-1",
            "title": "Week 1",
            "problem_ids": ["problem-1"],
        },
    )
    assert assignment.status_code == 200
    assert calls[0][0] == "PUT"
    assert calls[1][1].endswith("cat_id=cat%201")
    assert calls[2][0] == "POST"


def test_assignment_validates_limits_and_fallback(monkeypatch):
    """Assignments enforce pond identity and the 100-problem limit."""

    payload = {
        "cat_id": "cat-1",
        "pond_id": "pond-1",
        "title": "Too Many",
        "problem_ids": [f"problem-{index}" for index in range(101)],
    }
    assert (
        client.post("/teacher/ponds/other/assignments", json=payload).status_code == 400
    )
    assert (
        client.post("/teacher/ponds/pond-1/assignments", json=payload).status_code
        == 400
    )

    async def fake_forward(method, path, payload=None):
        raise teacher_main.HTTPException(status_code=404, detail="not ready")

    monkeypatch.setattr(teacher_main, "forward_to_game_service", fake_forward)
    payload["problem_ids"] = ["problem-1"]
    response = client.post("/teacher/ponds/pond-1/assignments", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "queued_template"


@pytest.mark.parametrize("path", ["/teacher/ponds/other/invites"])
def test_invites_validate_pond_id(path):
    """Private pond invitations reject path/body mismatches."""

    response = client.post(
        path,
        json={
            "cat_id": "cat-1",
            "pond_id": "pond-1",
            "student_emails": ["student@example.com"],
            "room_code": "ABC123",
        },
    )
    assert response.status_code == 400


def test_invites_return_room_code_template():
    """Private pond invitations expose room code email metadata."""

    response = client.post(
        "/teacher/ponds/pond-1/invites",
        json={
            "cat_id": "cat-1",
            "pond_id": "pond-1",
            "student_emails": ["student@example.com"],
            "room_code": "ABC123",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "template_ready"
    assert body["room_code"] == "ABC123"
