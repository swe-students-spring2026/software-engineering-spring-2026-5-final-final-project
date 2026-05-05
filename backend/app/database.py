from motor.motor_asyncio import AsyncIOMotorClient
from app.config import get_settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(get_settings().mongodb_uri)
    return _client


def get_database():
    return get_client()["vibe"]


def get_users_collection():
    return get_database()["users"]


def get_likes_collection():
    return get_database()["likes"]


def get_matches_collection():
    return get_database()["matches"]


async def create_indexes():
    users = get_users_collection()
    await users.create_index("email", unique=True)
    await users.create_index("city")
    await users.create_index("is_spotify_connected")

    likes = get_likes_collection()
    await likes.create_index([("from_user_id", 1), ("to_user_id", 1)], unique=True)
    await likes.create_index("to_user_id")

    matches = get_matches_collection()
    await matches.create_index("user_ids")
