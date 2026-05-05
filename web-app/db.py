"""
MongoDB integration for caching search results.
Avoids re-running the expensive ML pipeline for repeated queries.

Requires MONGO_URI environment variable to be set, e.g.:
    MONGO_URI=mongodb://localhost:27017/rove_beetle
"""

import os
import hashlib
import json
from datetime import datetime, timezone

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure


MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/rove_beetle")
DB_NAME = "rove_beetle"
COLLECTION_NAME = "search_cache"


def get_db():
    """Return the MongoDB database instance."""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    return client[DB_NAME]


def make_cache_key(query_311: str, query_facilities: str) -> str:
    """Create a unique hash key from the two search queries."""
    raw = f"{query_311.strip().lower()}||{query_facilities.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_cached_result(query_311: str, query_facilities: str):
    """
    Look up a cached search result in MongoDB.
    Returns the cluster_results list if found, None otherwise.
    """
    try:
        db = get_db()
        key = make_cache_key(query_311, query_facilities)
        doc = db[COLLECTION_NAME].find_one({"_id": key})

        if doc:
            return doc["cluster_results"]

        return None

    except ConnectionFailure:
        # if mongo is down, just skip the cache
        return None

    except Exception:
        return None


def save_cached_result(query_311: str, query_facilities: str, cluster_results: list):
    """
    Save a search result to MongoDB cache.
    Uses upsert so repeated searches overwrite the old cache entry.
    """
    try:
        db = get_db()
        key = make_cache_key(query_311, query_facilities)

        db[COLLECTION_NAME].update_one(
            {"_id": key},
            {
                "$set": {
                    "query_311": query_311,
                    "query_facilities": query_facilities,
                    "cluster_results": cluster_results,
                    "cached_at": datetime.now(timezone.utc).isoformat(),
                }
            },
            upsert=True,
        )

    except ConnectionFailure:
        # if mongo is down, just skip saving
        pass

    except Exception:
        pass


def clear_cache():
    """Clear all cached search results. Useful for testing."""
    try:
        db = get_db()
        db[COLLECTION_NAME].delete_many({})

    except Exception:
        pass


def health_check() -> bool:
    """Check if MongoDB is reachable. Returns True if ok, False otherwise."""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        return True

    except Exception:
        return False