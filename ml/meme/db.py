from __future__ import annotations

import os
from typing import Any

from bson import ObjectId
from pymongo import DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

DEFAULT_DB_NAME = "meme_generator"
DEFAULT_COLLECTION_NAME = "generated_memes"

_client: MongoClient | None = None


def get_database() -> Database | None:
    global _client

    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        return None

    if _client is None:
        _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)

    db_name = os.getenv("MONGODB_DB_NAME", DEFAULT_DB_NAME)
    return _client[db_name]


def get_collection() -> Collection | None:
    database = get_database()
    if database is None:
        return None

    collection_name = os.getenv("MONGODB_COLLECTION_NAME", DEFAULT_COLLECTION_NAME)
    return database[collection_name]


def serialize_record(record: dict[str, Any]) -> dict[str, Any]:
    serialized = dict(record)
    serialized["id"] = str(serialized.pop("_id"))
    return serialized


def save_meme_record(record: dict[str, Any]) -> str | None:
    collection = get_collection()
    if collection is None:
        return None

    result = collection.insert_one(record)
    return str(result.inserted_id)


def get_recent_memes(limit: int = 20) -> list[dict[str, Any]]:
    collection = get_collection()
    if collection is None:
        raise RuntimeError(
            "MongoDB is not configured. Set MONGODB_URI to enable history."
        )

    documents = collection.find().sort("created_at", DESCENDING).limit(limit)
    return [serialize_record(document) for document in documents]


def get_meme_by_id(record_id: str) -> dict[str, Any] | None:
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
    database = get_database()
    if database is None:
        return False

    try:
        database.command("ping")
    except PyMongoError:
        return False

    return True
