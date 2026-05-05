"""Tests for database helper functions."""

# pylint: disable=too-few-public-methods,unnecessary-lambda

import pytest
from bson import ObjectId
from pymongo.errors import PyMongoError

from app import db
from app.db import (
    get_collection,
    get_database,
    get_meme_by_id,
    ping_database,
    save_meme_record,
    serialize_record,
)


class FakeInsertResult:
    """Fake MongoDB insert result."""

    inserted_id = ObjectId()


class FakeCursor:
    """Fake MongoDB cursor with sort and limit chaining."""

    def __init__(self, documents):
        self.documents = documents

    def sort(self, _field, _direction):
        """Return the same cursor after sorting."""
        return self

    def limit(self, _limit):
        """Return the same cursor after limiting."""
        return self

    def __iter__(self):
        """Iterate over fake documents."""
        return iter(self.documents)


class FakeCollection:
    """Fake MongoDB collection."""

    def __init__(self, document=None):
        self.document = document

    def insert_one(self, _record):
        """Return a fake inserted id."""
        return FakeInsertResult()

    def find(self):
        """Return a fake cursor."""
        return FakeCursor([self.document])

    def find_one(self, _query):
        """Return the configured fake document."""
        return self.document


class FakeDatabase:
    """Fake MongoDB database."""

    def __init__(self, command_error=None):
        self.command_error = command_error

    def __getitem__(self, _name):
        """Return a fake collection."""
        return FakeCollection({"_id": ObjectId(), "summary": "fake summary"})

    def command(self, _name):
        """Optionally raise a fake command error."""
        if self.command_error is not None:
            raise self.command_error

        return {"ok": 1}


class FakeClient:
    """Fake MongoDB client."""

    def __getitem__(self, _name):
        """Return a fake database."""
        return FakeDatabase()


def test_serialize_record_converts_id():
    """Check that MongoDB object ids are exposed as strings."""
    object_id = ObjectId()

    assert serialize_record({"_id": object_id, "summary": "fake summary"}) == {
        "id": str(object_id),
        "summary": "fake summary",
    }


def test_get_database_uses_configured_client(monkeypatch):
    """Check database selection from environment configuration."""
    monkeypatch.setenv("MONGODB_URI", "mongodb://example")
    monkeypatch.setenv("MONGODB_DB_NAME", "test_db")
    monkeypatch.setattr(db, "get_client", lambda _uri: FakeClient())

    assert isinstance(get_database(), FakeDatabase)


def test_get_collection_uses_configured_collection(monkeypatch):
    """Check collection selection from environment configuration."""
    monkeypatch.setattr(db, "get_database", lambda: FakeDatabase())

    assert isinstance(get_collection(), FakeCollection)


def test_save_meme_record_without_mongodb(monkeypatch):
    """Check that saving is skipped when MongoDB is not configured."""
    monkeypatch.delenv("MONGODB_URI", raising=False)

    assert save_meme_record({"summary": "fake summary", "image": "meme.png"}) is None


def test_save_meme_record_returns_inserted_id(monkeypatch):
    """Check that saving returns the inserted record id."""
    monkeypatch.setattr(db, "get_collection", lambda: FakeCollection())

    assert ObjectId.is_valid(save_meme_record({"summary": "fake summary"}))


def test_get_recent_memes_returns_serialized_records(monkeypatch):
    """Check that recent memes are serialized."""
    object_id = ObjectId()
    monkeypatch.setattr(
        db, "get_collection", lambda: FakeCollection({"_id": object_id, "summary": "x"})
    )

    assert db.get_recent_memes() == [{"id": str(object_id), "summary": "x"}]


def test_get_recent_memes_without_mongodb(monkeypatch):
    """Check that recent meme reads require MongoDB configuration."""
    monkeypatch.setattr(db, "get_collection", lambda: None)

    with pytest.raises(RuntimeError):
        db.get_recent_memes()


def test_get_meme_by_id_rejects_invalid_id(monkeypatch):
    """Check invalid MongoDB object ids return no result."""
    monkeypatch.setattr(db, "get_collection", lambda: FakeCollection())

    assert get_meme_by_id("not-an-object-id") is None


def test_get_meme_by_id_returns_none_for_missing_doc(monkeypatch):
    """Check missing MongoDB documents return no result."""
    monkeypatch.setattr(db, "get_collection", lambda: FakeCollection())

    assert get_meme_by_id(str(ObjectId())) is None


def test_get_meme_by_id_returns_serialized_record(monkeypatch):
    """Check single meme lookup returns a serialized record."""
    object_id = ObjectId()
    monkeypatch.setattr(
        db, "get_collection", lambda: FakeCollection({"_id": object_id, "summary": "x"})
    )

    assert get_meme_by_id(str(object_id)) == {"id": str(object_id), "summary": "x"}


def test_ping_database_without_mongodb(monkeypatch):
    """Check that database ping reports false when MongoDB is not configured."""
    monkeypatch.delenv("MONGODB_URI", raising=False)

    assert ping_database() is False


def test_ping_database_returns_true(monkeypatch):
    """Check successful database ping."""
    monkeypatch.setattr(db, "get_database", lambda: FakeDatabase())

    assert ping_database() is True


def test_ping_database_handles_errors(monkeypatch):
    """Check failed database ping."""
    monkeypatch.setattr(db, "get_database", lambda: FakeDatabase(PyMongoError()))

    assert ping_database() is False


def test_get_meme_by_id_without_mongodb(monkeypatch):
    """Check that reads require MongoDB configuration."""
    monkeypatch.delenv("MONGODB_URI", raising=False)

    with pytest.raises(RuntimeError):
        get_meme_by_id(str(ObjectId()))
