"""tests for ML logic."""

from app.model import predict


def test_predict_empty():
    """check empty input."""
    assert predict("") == "no input"


def test_predict_negative():
    """check negative text."""
    assert predict("this is bad") == "negative"


def test_predict_positive():
    """check positive text."""
    assert predict("this is good") == "positive"
