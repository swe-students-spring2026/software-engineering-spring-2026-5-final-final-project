"""tests for fake db helpers."""

from app.db import save_last_result


def test_save_last_result_empty():
    """theck empty result is not saved."""
    assert save_last_result({}) is False


def test_save_last_result_normal():
    """theck normal result is saved."""
    result = {"summary": "fake summary", "image": "meme.png"}
    assert save_last_result(result) is True
