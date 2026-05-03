"""tests for scraper functions."""

import pytest

from app.logic.scraper import clean_text, get_article


def test_clean_text_spaces():
    """check extra spaces are removed."""
    text = "  this   is   news  "
    assert clean_text(text) == "this is news"


def test_clean_text_empty():
    """check empty string stays empty."""
    assert clean_text("") == ""


def test_get_article_no_url():
    """check missing URL raises error."""
    with pytest.raises(ValueError):
        get_article("")


def test_get_article_fake():
    """checking fake article."""
    assert get_article("https://example.com") == "fake article text"
