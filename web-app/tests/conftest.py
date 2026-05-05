# tests/conftest.py
import pytest
from unittest.mock import patch, MagicMock

with patch("app.db", MagicMock()):
    from app import app as flask_app

@pytest.fixture
def client():
    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-key",
    })
    
    with flask_app.test_client() as client:
        
        yield client


@pytest.fixture
def logged_in_client(client):
    with client.session_transaction() as sess:
        sess["user_id"] = "test_user_123"
        sess["token_info"] = {"access_token": "fake-token"}
    return client


@pytest.fixture(autouse=True)
def mock_db():
    with patch("app.db") as mock:
        
        yield mock