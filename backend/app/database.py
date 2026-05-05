import motor.motor_asyncio
from app.config import get_settings

_client: motor.motor_asyncio.AsyncIOMotorClient | None = None


def _get_client() -> motor.motor_asyncio.AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = motor.motor_asyncio.AsyncIOMotorClient(get_settings().mongodb_uri)
    return _client


def get_users_collection():
    return _get_client()["vibe"]["users"]


def get_likes_collection():
    return _get_client()["vibe"]["likes"]


def get_matches_collection():
    return _get_client()["vibe"]["matches"]
