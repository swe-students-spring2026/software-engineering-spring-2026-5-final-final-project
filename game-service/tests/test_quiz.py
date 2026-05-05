from unittest.mock import AsyncMock, patch

import httpx
import pytest

# --- GET /quiz/problems ---


def test_list_problems(client):
    resp = client.get("/quiz/problems")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 5
    for p in data:
        assert set(p.keys()) == {
            "id",
            "title",
            "difficulty",
            "fishing_reward",
            "completed",
            "exhausted",
            "attempts_used",
        }


def test_list_problems_does_not_expose_test_code(client):
    resp = client.get("/quiz/problems")
    assert resp.status_code == 200
    for p in resp.json():
        assert "test_code" not in p
        assert "starter_code" not in p


# --- GET /quiz/problems/{id} ---


def test_get_problem_404_for_missing(client):
    resp = client.get("/quiz/problems/does-not-exist")
    assert resp.status_code == 404


def test_get_problem_returns_starter_and_instructions(client):
    resp = client.get("/quiz/problems/leap")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "leap"
    assert data["function_name"] == "leap_year"
    assert "leap_year" in data["starter_code"]
    assert "leap year" in data["instructions"].lower()


def test_get_problem_does_not_expose_test_code(client):
    resp = client.get("/quiz/problems/leap")
    assert "test_code" not in resp.json()


# --- POST /quiz/problems/{id}/submit ---


@patch("app.routers.quiz.grader_client", new_callable=lambda: AsyncMock())
def test_submit_passes_grants_fishing_reward(mock_grader, client):
    mock_grader.grade.return_value = {
        "passed": True,
        "tests_run": 9,
        "tests_passed": 9,
    }

    resp = client.post(
        "/quiz/problems/leap/submit",
        json={"code": "def leap_year(y): return True", "user_id": "u1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is True
    assert data["fishing_reward_granted"] == 1
    assert data["new_fishing_chances"] == 1


@patch("app.routers.quiz.grader_client", new_callable=lambda: AsyncMock())
def test_submit_accumulates_fishing_chances(mock_grader, client):
    mock_grader.grade.return_value = {"passed": True, "tests_run": 9, "tests_passed": 9}

    client.post(
        "/quiz/problems/leap/submit",
        json={"code": "def leap_year(y): return True", "user_id": "u1"},
    )
    resp = client.post(
        "/quiz/problems/isogram/submit",  # reward is 2 for isogram
        json={"code": "def is_isogram(s): return True", "user_id": "u1"},
    )
    assert resp.status_code == 200
    assert resp.json()["new_fishing_chances"] == 3  # 1 + 2


@patch("app.routers.quiz.grader_client", new_callable=lambda: AsyncMock())
def test_submit_fails_no_reward(mock_grader, client):
    mock_grader.grade.return_value = {
        "passed": False,
        "tests_run": 9,
        "tests_passed": 3,
        "failed_test": "test_year_divisible_by_400_is_leap_year",
    }

    resp = client.post(
        "/quiz/problems/leap/submit",
        json={"code": "def leap_year(y): return False"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is False
    assert data["fishing_reward_granted"] == 0
    assert data["new_fishing_chances"] is None
    assert data["failed_test"] == "test_year_divisible_by_400_is_leap_year"
    assert data["solution_revealed"] is False


@patch("app.routers.quiz.grader_client", new_callable=lambda: AsyncMock())
def test_submit_reveals_solution_after_five_failed_attempts(mock_grader, client):
    mock_grader.grade.return_value = {
        "passed": False,
        "tests_run": 9,
        "tests_passed": 0,
        "failed_test": "test_year_divisible_by_400_is_leap_year",
    }

    final_response = None
    for _ in range(5):
        final_response = client.post(
            "/quiz/problems/leap/submit",
            json={"code": "def leap_year(year): return False", "user_id": "u2"},
        )

    assert final_response is not None
    assert final_response.status_code == 200
    data = final_response.json()
    assert data["passed"] is False
    assert data["attempts_used"] == 5
    assert data["attempts_remaining"] == 0
    assert data["solution_revealed"] is True
    assert "def leap_year" in data["solution_code"]
    assert data["added_to_uncaught_fish"] is True
    assert data["tokens_lost"] == 1

    uncaught = client.get("/quiz/uncaught/u2")
    assert uncaught.status_code == 200
    assert uncaught.json()[0]["problem_id"] == "leap"


def test_submit_404_for_missing_problem(client):
    resp = client.post(
        "/quiz/problems/does-not-exist/submit",
        json={"code": "x = 1"},
    )
    assert resp.status_code == 404


@patch("app.routers.quiz.grader_client", new_callable=lambda: AsyncMock())
def test_submit_502_when_grader_unreachable(mock_grader, client):
    mock_grader.grade.side_effect = httpx.ConnectError("connection refused")

    resp = client.post(
        "/quiz/problems/leap/submit",
        json={"code": "x = 1"},
    )
    assert resp.status_code == 502


def test_submit_rejects_empty_code(client):
    resp = client.post(
        "/quiz/problems/leap/submit",
        json={"code": ""},
    )
    # Pydantic min_length=1 should reject this with 422
    assert resp.status_code == 422


# --- /health ---


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
