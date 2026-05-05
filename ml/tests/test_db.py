"""Tests for ML MongoDB helpers."""

import pytest
from bson import ObjectId
from pymongo.errors import PyMongoError

from meme import db
from meme.db import (
    get_collection,
    get_database,
    get_meme_by_id,
    get_recent_memes,
    ping_database,
    save_meme_record,
    serialize_record,
)


class FakeInsertResult:
    """Fake MongoDB insert result."""

    inserted_id = ObjectId()


class FakeCursor:
    """Fake MongoDB cursor."""

    def __init__(self, documents):
        self.documents = documents

    def sort(self, _field, _direction):
        """Return self after sort."""
        return self

    def limit(self, _limit):
        """Return self after limit."""
        return self

    def __iter__(self):
        """Iterate over documents."""
        return iter(self.documents)


class FakeCollection:
    """Fake MongoDB collection."""

    def __init__(self, document=None):
        self.document = document

    def insert_one(self, _record):
        """Return a fake insert result."""
        return FakeInsertResult()

    def find(self):
        """Return fake cursor."""
        return FakeCursor([self.document])

    def find_one(self, _query):
        """Return fake document."""
        return self.document


class FakeDatabase:
    """Fake MongoDB database."""

    def __init__(self, command_error=None):
        self.command_error = command_error

    def __getitem__(self, _name):
        """Return fake collection."""
        return FakeCollection({"_id": ObjectId(), "summary": "x"})

    def command(self, _name):
        """Return or raise fake ping result."""
        if self.command_error:
            raise self.command_error
        return {"ok": 1}


class FakeClient:
    """Fake MongoDB client."""

    def __getitem__(self, _name):
        """Return fake database."""
        return FakeDatabase()


def test_get_database_without_uri(monkeypatch):
    """Check missing MongoDB URI disables DB."""
    monkeypatch.delenv("MONGODB_URI", raising=False)
    monkeypatch.setattr(db, "_client", None)

    assert get_database() is None


def test_get_database_with_uri(monkeypatch):
    """Check configured database lookup."""
    monkeypatch.setenv("MONGODB_URI", "mongodb://example")
    monkeypatch.setenv("MONGODB_DB_NAME", "test_db")
    monkeypatch.setattr(db, "MongoClient", lambda *_args, **_kwargs: FakeClient())
    monkeypatch.setattr(db, "_client", None)

    assert isinstance(get_database(), FakeDatabase)


def test_get_collection_without_database(monkeypatch):
    """Check missing database disables collection."""
    monkeypatch.setattr(db, "get_database", lambda: None)

    assert get_collection() is None


def test_get_collection_with_database(monkeypatch):
    """Check configured collection lookup."""
    monkeypatch.setattr(db, "get_database", lambda: FakeDatabase())

    assert isinstance(get_collection(), FakeCollection)


def test_serialize_record_converts_id():
    """Check MongoDB id serialization."""
    object_id = ObjectId()

    assert serialize_record({"_id": object_id, "summary": "x"}) == {
        "id": str(object_id),
        "summary": "x",
    }


def test_save_meme_record_without_collection(monkeypatch):
    """Check save skips when DB is disabled."""
    monkeypatch.setattr(db, "get_collection", lambda: None)

    assert save_meme_record({"summary": "x"}) is None


def test_save_meme_record_returns_inserted_id(monkeypatch):
    """Check save returns inserted id."""
    monkeypatch.setattr(db, "get_collection", lambda: FakeCollection())

    assert ObjectId.is_valid(save_meme_record({"summary": "x"}))


def test_get_recent_memes_without_collection(monkeypatch):
    """Check history requires DB."""
    monkeypatch.setattr(db, "get_collection", lambda: None)

    with pytest.raises(RuntimeError):
        get_recent_memes()


def test_get_recent_memes_serializes_records(monkeypatch):
    """Check history serializes records."""
    object_id = ObjectId()
    monkeypatch.setattr(
        db, "get_collection", lambda: FakeCollection({"_id": object_id, "summary": "x"})
    )

    assert get_recent_memes() == [{"id": str(object_id), "summary": "x"}]


def test_get_meme_by_id_without_collection(monkeypatch):
    """Check lookup requires DB."""
    monkeypatch.setattr(db, "get_collection", lambda: None)

    with pytest.raises(RuntimeError):
        get_meme_by_id(str(ObjectId()))


def test_get_meme_by_id_rejects_invalid_id(monkeypatch):
    """Check invalid object id."""
    monkeypatch.setattr(db, "get_collection", lambda: FakeCollection())

    assert get_meme_by_id("bad") is None


def test_get_meme_by_id_returns_none_for_missing_doc(monkeypatch):
    """Check missing record."""
    monkeypatch.setattr(db, "get_collection", lambda: FakeCollection())

    assert get_meme_by_id(str(ObjectId())) is None


def test_get_meme_by_id_serializes_record(monkeypatch):
    """Check found record serialization."""
    object_id = ObjectId()
    monkeypatch.setattr(
        db, "get_collection", lambda: FakeCollection({"_id": object_id, "summary": "x"})
    )

    assert get_meme_by_id(str(object_id)) == {"id": str(object_id), "summary": "x"}


def test_ping_database_without_database(monkeypatch):
    """Check ping without DB."""
    monkeypatch.setattr(db, "get_database", lambda: None)

    assert ping_database() is False


def test_ping_database_success(monkeypatch):
    """Check ping success."""
    monkeypatch.setattr(db, "get_database", lambda: FakeDatabase())

    assert ping_database() is True


def test_ping_database_failure(monkeypatch):
    """Check ping failure."""
    monkeypatch.setattr(db, "get_database", lambda: FakeDatabase(PyMongoError()))

    assert ping_database() is False
