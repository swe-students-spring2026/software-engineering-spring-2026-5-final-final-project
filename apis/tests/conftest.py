import os
import sys
from unittest.mock import MagicMock, patch

# Set env vars before any app module is imported
os.environ["GEMINI_API_KEY"] = "test_key_for_ci"
os.environ["GEMINI_MODEL"] = "gemini-2.0-flash"
os.environ["MONGO_URI"] = "mongodb://localhost:27017/test"
os.environ["MONGO_DB_NAME"] = "test"
os.environ["API_INTERNAL_TOKEN"] = "test-internal-token"

# Stub google.genai so the AI service can be imported without a real key
_mock_genai_module = MagicMock()
sys.modules.setdefault("google", MagicMock())
sys.modules.setdefault("google.genai", _mock_genai_module)
sys.modules.setdefault("google.genai.types", MagicMock())

# Ensure the apis package is importable when running tests from repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

# Shared mock database — configured once, reused across all tests
_mock_db = MagicMock()
_mock_mongo = MagicMock()
_mock_mongo.__getitem__ = MagicMock(return_value=_mock_db)

# Import the Flask app with MongoClient patched so no real connection is made
with patch("pymongo.MongoClient", return_value=_mock_mongo):
    from app.main import app as _flask_app

_flask_app.config["TESTING"] = True


@pytest.fixture(scope="session")
def flask_app():
    return _flask_app


@pytest.fixture(scope="session")
def mock_db():
    return _mock_db


@pytest.fixture
def client(flask_app):
    with flask_app.test_client() as c:
        c.environ_base["HTTP_X_INTERNAL_API_TOKEN"] = "test-internal-token"
        yield c
