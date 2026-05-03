"""tests for route helper functions."""

import pytest

from app.routes import check_url, make_request_data, show_error


def test_check_url_empty():
    """check empty url."""
    assert check_url("") is False


def test_check_url_normal():
    """check normal url."""
    assert check_url("https://example.com") is True


def test_make_request_data_empty():
    """check missing url error."""
    with pytest.raises(ValueError):
        make_request_data("")


def test_make_request_data_normal():
    """check request data."""
    assert make_request_data("https://example.com") == {"url": "https://example.com"}


def test_show_error():
    """check error message."""
    assert show_error("bad url") == "error: bad url"
