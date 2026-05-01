import pytest
from unittest.mock import patch
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_health_route(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}

@patch("app.analyze_assignment")
def test_analyze_route(mock_analyze_assignment, client):
    mock_analyze_assignment.return_value = {
        "difficulty": 4,
        "priority": "high",
        "estimated_hours": 5
    }

    response = client.post("/analyze", json={
        "title": "Final Project",
        "course": "Software Engineering",
        "description": "Finish Docker and CI/CD",
        "due_date": "2026-05-05"
    })

    assert response.status_code == 200
    data = response.get_json()
    assert data["difficulty"] == 4
    assert data["priority"] == "high"
    assert data["estimated_hours"] == 5

    mock_analyze_assignment.assert_called_once_with(
        title="Final Project",
        course="Software Engineering",
        description="Finish Docker and CI/CD",
        due_date="2026-05-05"
    )