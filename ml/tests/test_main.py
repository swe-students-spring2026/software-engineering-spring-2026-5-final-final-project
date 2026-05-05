"""Tests for ML FastAPI service helpers."""

from datetime import datetime

import pytest
from fastapi import HTTPException

from meme import main
from meme.captioner import MemeCaption
from meme.main import GenerateRequest, build_record, generate_meme, health


def test_database_status_not_configured(monkeypatch):
    """Check missing database configuration."""
    monkeypatch.delenv("MONGODB_URI", raising=False)

    assert main.database_status() == "not_configured"


def test_database_status_connected(monkeypatch):
    """Check successful database status."""
    monkeypatch.setenv("MONGODB_URI", "mongodb://example")
    monkeypatch.setattr(main, "ping_database", lambda: True)

    assert main.database_status() == "connected"


def test_database_status_unreachable(monkeypatch):
    """Check failed database status."""
    monkeypatch.setenv("MONGODB_URI", "mongodb://example")
    monkeypatch.setattr(main, "ping_database", lambda: False)

    assert main.database_status() == "unreachable"


def test_build_record():
    """Check generated record shape."""
    payload = GenerateRequest(
        person_name="Ada",
        text="Article summary",
        source_url="https://example.com",
        template="drake",
    )
    response = {
        "template": "drake",
        "top_text": "top",
        "bottom_text": "bottom",
        "meme_url": "https://example.com/meme.png",
    }

    record = build_record(payload, response)

    assert record["person_name"] == "Ada"
    assert record["source_url"] == "https://example.com"
    assert record["article_text"] == "Article summary"
    assert record["article_summary"] == "Article summary"
    assert record["template"] == "drake"
    assert isinstance(record["created_at"], datetime)


def test_health(monkeypatch):
    """Check health response."""
    monkeypatch.setattr(main, "database_status", lambda: "connected")

    assert health() == {"status": "ok", "database": "connected"}


def test_templates():
    """Check templates response."""
    assert "buzz" in main.templates()["templates"]


def test_history(monkeypatch):
    """Check history response."""
    monkeypatch.setattr(main, "get_recent_memes", lambda limit: [{"id": "1"}])

    assert main.history(limit=1) == {"items": [{"id": "1"}]}


def test_history_item_not_found(monkeypatch):
    """Check missing history item."""
    monkeypatch.setattr(main, "get_meme_by_id", lambda _record_id: None)

    with pytest.raises(HTTPException) as exc_info:
        main.history_item("missing")

    assert exc_info.value.status_code == 404


def test_history_item_found(monkeypatch):
    """Check found history item."""
    monkeypatch.setattr(main, "get_meme_by_id", lambda _record_id: {"id": "1"})

    assert main.history_item("1") == {"id": "1"}


def test_generate_meme(monkeypatch):
    """Check meme generation response."""
    monkeypatch.setattr(
        main, "generate_caption", lambda _text: MemeCaption(top="top", bottom="bottom")
    )
    monkeypatch.setattr(main, "save_meme_record", lambda _record: "record-1")

    response = generate_meme(
        GenerateRequest(person_name="Ada", text="Article summary", template="drake")
    )

    assert response == {
        "template": "drake",
        "top_text": "top",
        "bottom_text": "bottom",
        "meme_url": "https://api.memegen.link/images/drake/top/bottom.png",
        "person_name": "Ada",
        "source_url": None,
        "article_summary": "Article summary",
        "record_id": "record-1",
    }
