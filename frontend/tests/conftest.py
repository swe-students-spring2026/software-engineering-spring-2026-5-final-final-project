import os
import pytest

os.environ.setdefault("API_URL", "http://test-backend:8000")
os.environ.setdefault("FRONTEND_INTERNAL_PORT", "3000")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key")
os.environ.setdefault("GOOGLE_CLIENT_ID", "")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "")


@pytest.fixture(scope="session")
def flask_app():
    from app.main import app
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    return app


@pytest.fixture
def client(flask_app):
    """Authenticated test client with a logged-in NYU session."""
    with flask_app.test_client() as c:
        with c.session_transaction() as sess:
            sess["user"] = {"email": "test@nyu.edu", "name": "Test User"}
        yield c


@pytest.fixture
def anon_client(flask_app):
    """Unauthenticated test client."""
    with flask_app.test_client() as c:
        yield c
