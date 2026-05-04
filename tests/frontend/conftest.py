import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Must happen before any frontend import so flask_pymongo is never the real module
sys.modules.setdefault("flask_pymongo", MagicMock())

os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/testdb")
os.environ.setdefault("SECRET_KEY", "test-secret")

from app import app as _flask_app  # noqa: E402  (import after env setup)


@pytest.fixture(scope="session")
def app():
    _flask_app.config["TESTING"] = True
    _flask_app.config["SECRET_KEY"] = "test-secret"
    return _flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def reset_mongo():
    """Give each test a fresh MagicMock for mongo.db."""
    import db
    db.mongo.db = MagicMock()
    yield
