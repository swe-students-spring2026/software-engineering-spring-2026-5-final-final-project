"""tests for main app functions."""

import pytest

from app.main import health, make_meme


def test_health():
    """check health function returns ok."""
    assert health() == {"status": "ok"}


def test_make_meme_no_url():
    """check error when URL is missing."""
    with pytest.raises(ValueError):
        make_meme("")


def test_make_meme():
    """check full meme generation flow."""
    result = make_meme("https://example.com")

    assert result["url"] == "https://example.com"
    assert result["summary"] == "fake summary"
    assert result["image"] == "meme_1.png"
