"""tests for config values."""

from app.config import APP_NAME, BACKEND_URL


def test_app_name():
    """check app name."""
    assert APP_NAME == "News2Meme"


def test_backend_url():
    """check backend url."""
    assert BACKEND_URL == "http://backend:8000"
