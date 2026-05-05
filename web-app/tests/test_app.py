"""Tests for app creation."""

from app import create_app


def test_create_app():
    """check flask app is created."""
    test_app = create_app()

    assert test_app is not None
    assert test_app.name == "app"


def test_health_route_does_not_require_database(monkeypatch):
    """Check health route can boot without a reachable database."""
    monkeypatch.setenv(
        "MONGODB_URI",
        "mongodb+srv://user:pass@example.mongodb.net/?retryWrites=true&w=majority",
    )
    test_app = create_app()
    client = test_app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
