"""tests for summary functions."""

from app.logic.sum import make_summary


def test_make_summary_empty():
    """check summary when article is empty."""
    assert make_summary("") == "no article"


def test_make_summary_fake():
    """check fake summary output."""
    assert make_summary("long article text") == "fake summary"
