"""MongoDB helpers for storing and reading generated meme records."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from bson import ObjectId
from pymongo import DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

DEFAULT_DB_NAME = "meme_generator"
DEFAULT_COLLECTION_NAME = "generated_memes"


@lru_cache(maxsize=1)
def get_client(mongo_uri: str) -> MongoClient:
    """Return a cached MongoDB client for the configured URI."""
    return MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)


def get_database() -> Database | None:
    """Return the configured MongoDB database, or None when MongoDB is disabled."""

    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        return None

    db_name = os.getenv("MONGODB_DB_NAME", DEFAULT_DB_NAME)
    return get_client(mongo_uri)[db_name]


def get_collection() -> Collection | None:
    """Return the configured meme collection, or None when MongoDB is disabled."""
    database = get_database()
    if database is None:
        return None

    collection_name = os.getenv("MONGODB_COLLECTION_NAME", DEFAULT_COLLECTION_NAME)
    return database[collection_name]


def serialize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Convert a MongoDB document into a JSON-friendly record."""
    serialized = dict(record)
    serialized["id"] = str(serialized.pop("_id"))
    return serialized


def save_meme_record(record: dict[str, Any]) -> str | None:
    """Save a meme record and return its inserted id."""
    collection = get_collection()
    if collection is None:
        return None

    result = collection.insert_one(record)
    return str(result.inserted_id)


def get_recent_memes(limit: int = 20) -> list[dict[str, Any]]:
    """Return recently generated memes, newest first."""
    collection = get_collection()
    if collection is None:
        raise RuntimeError(
            "MongoDB is not configured. Set MONGODB_URI to enable history."
        )

    documents = collection.find().sort("created_at", DESCENDING).limit(limit)
    return [serialize_record(document) for document in documents]


def get_meme_by_id(record_id: str) -> dict[str, Any] | None:
    """Return one meme by MongoDB object id."""
    collection = get_collection()
    if collection is None:
        raise RuntimeError(
            "MongoDB is not configured. Set MONGODB_URI to enable history."
        )

    if not ObjectId.is_valid(record_id):
        return None

    document = collection.find_one({"_id": ObjectId(record_id)})
    if document is None:
        return None

    return serialize_record(document)


def ping_database() -> bool:
    """Return whether the configured MongoDB server responds to ping."""
    database = get_database()
    if database is None:
        return False

    try:
        database.command("ping")
    except PyMongoError:
        return False

    return True
