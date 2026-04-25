import os
import pytest

os.environ.setdefault("API_URL", "http://test-backend:8000")
os.environ.setdefault("FRONTEND_INTERNAL_PORT", "3000")


@pytest.fixture(scope="session")
def flask_app():
    from app.main import app
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(flask_app):
    with flask_app.test_client() as c:
        yield c
