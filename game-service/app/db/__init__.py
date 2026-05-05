from app.config import settings
from app.db.repository import Repository
from app.db.mock_repo import MockRepository
from app.db.mongo_repo import MongoRepository


def get_repository() -> Repository:
    """Factory. Reads DB_BACKEND env to pick implementation."""
    if settings.db_backend == "mock":
        return MockRepository.get_instance()
    if settings.db_backend == "mongo":
        return MongoRepository.get_instance()
    raise ValueError(f"Unknown db_backend: {settings.db_backend}")
