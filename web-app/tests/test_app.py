"""tests for web app main functions."""

from app.main import health, home_text, result_text


def test_health():
    """check health function."""
    assert health() == {"status": "ok"}


def test_home_text():
    """check home page text."""
    assert home_text() == "News2Meme"


def test_result_text_missing_summary():
    """check missing summary result."""
    assert result_text("", "image.png") == "missing result"


def test_result_text_missing_image():
    """check missing image result."""
    assert result_text("summary", "") == "missing result"


def test_result_text_normal():
    """check normal result text."""
    assert result_text("news summary", "meme.png") == (
        "summary: news summary image: meme.png"
    )
