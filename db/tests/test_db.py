"""tests for database helpers."""

import pytest

from app.db import is_valid_record, make_meme_record


def test_make_meme_record():
    """check database record."""
    record = make_meme_record("url", "summary", "image.png")

    assert record["url"] == "url"
    assert record["summary"] == "summary"
    assert record["image"] == "image.png"


def test_make_meme_record_no_url():
    """check missing url."""
    with pytest.raises(ValueError):
        make_meme_record("", "summary", "image.png")


def test_is_valid_record_true():
    """check valid record."""
    record = {"url": "url", "summary": "summary", "image": "image.png"}

    assert is_valid_record(record) is True


def test_is_valid_record_false():
    """Check invalid record."""
    record = {"url": "url"}

    assert is_valid_record(record) is False
