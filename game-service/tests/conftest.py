import pytest
from fastapi.testclient import TestClient

from app.db.mock_repo import MockRepository


@pytest.fixture(autouse=True)
def reset_mock_repo():
    """Each test starts with a fresh in-memory repo singleton."""
    MockRepository.reset_instance()
    yield
    MockRepository.reset_instance()


@pytest.fixture
def client():
    # import inside the fixture so reset happens before the app reads any state
    from app.main import app

    return TestClient(app)
