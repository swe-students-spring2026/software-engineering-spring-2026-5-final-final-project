"""Tests for app creation."""

from app import create_app


def test_create_app():
    """check flask app is created."""
    test_app = create_app()

    assert test_app is not None
    assert test_app.name == "app"
