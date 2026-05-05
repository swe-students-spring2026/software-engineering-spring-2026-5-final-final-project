"""tests for storage functions."""

from app.logic.storage import make_doc


def test_make_doc():
    """check document stuffs are correct."""
    doc = make_doc(
        "url",
        "summary",
        "top text",
        "bottom text",
        "image.png",
    )

    assert doc["url"] == "url"
    assert doc["summary"] == "summary"
    assert doc["top"] == "top text"
    assert doc["bottom"] == "bottom text"
    assert doc["image"] == "image.png"
    assert "created_at" in doc
