"""
MongoDB integration for caching search results.
Avoids re-running the expensive ML pipeline for repeated queries.

Requires MONGO_URI environment variable to be set to a MongoDB Atlas connection string:
    MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/rove_beetle?retryWrites=true&w=majority
"""

import os
import hashlib
from datetime import datetime, timezone

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure


DB_NAME = "rove_beetle"
COLLECTION_NAME = "search_cache"

_client = None


def get_client():
    """Return a shared MongoClient instance."""
    global _client
    if _client is None:
        uri = os.environ.get("MONGO_URI")
        if not uri:
            raise RuntimeError(
                "MONGO_URI environment variable is not set. "
                "Use a MongoDB Atlas connection string."
            )
        _client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    return _client


def reset_client():
    """Reset the shared client. Used in tests to force a new connection."""
    global _client
    _client = None


def get_db():
    """Return the MongoDB database instance."""
    return get_client()[DB_NAME]


def make_cache_key(query: str, extra: str = "") -> str:
    """Create a unique hash key from the search query."""
    raw = f"{query.strip().lower()}||{extra.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_cached_result(query: str, extra: str = ""):
    """
    Look up a cached search result in MongoDB.
    Returns the cached data dict if found, None otherwise.
    """
    try:
        db = get_db()
        key = make_cache_key(query, extra)
        doc = db[COLLECTION_NAME].find_one({"_id": key})
        if doc:
            return doc.get("data")
        return None

    except ConnectionFailure:
        return None

    except Exception:
        return None


def save_cached_result(query: str, extra: str, data: dict):
    """
    Save a search result to MongoDB cache.
    Uses upsert so repeated searches overwrite the old cache entry.
    """
    try:
        db = get_db()
        key = make_cache_key(query, extra)
        db[COLLECTION_NAME].update_one(
            {"_id": key},
            {
                "$set": {
                    "query": query,
                    "data": data,
                    "cached_at": datetime.now(timezone.utc).isoformat(),
                }
            },
            upsert=True,
        )

    except ConnectionFailure:
        pass

    except Exception:
        pass


def clear_cache():
    """Clear all cached results. Useful for testing."""
    try:
        db = get_db()
        db[COLLECTION_NAME].delete_many({})
    except Exception:
        pass


def health_check() -> bool:
    """Check if MongoDB Atlas is reachable. Returns True if ok, False otherwise."""
    try:
        client = MongoClient(
            os.environ.get("MONGO_URI", ""),
            serverSelectionTimeoutMS=3000
        )
        client.admin.command("ping")
        return True
    except Exception:
        return False