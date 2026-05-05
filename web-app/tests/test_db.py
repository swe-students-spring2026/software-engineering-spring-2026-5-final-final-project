"""tests for web app database"""

from app import db


def test_serialize_record():
    """check Mongo _id becomes id string."""
    record = {"_id": "123", "summary": "fake summary"}

    result = db.serialize_record(record)

    assert result["id"] == "123"
    assert result["summary"] == "fake summary"
    assert "_id" not in result


def test_get_database_no_uri(monkeypatch):
    """database is none without env var."""
    monkeypatch.delenv("MONGODB_URI", raising=False)

    assert db.get_database() is None


def test_get_collection_no_database(monkeypatch):
    """collection is none without database."""
    monkeypatch.delenv("MONGODB_URI", raising=False)

    assert db.get_collection() is None


def test_save_meme_record_no_collection(monkeypatch):
    """save returns none if db is not configured."""
    monkeypatch.delenv("MONGODB_URI", raising=False)

    assert db.save_meme_record({"summary": "fake"}) is None


def test_ping_database_no_uri(monkeypatch):
    """ping is false if db is not configured."""
    monkeypatch.delenv("MONGODB_URI", raising=False)

    assert db.ping_database() is False