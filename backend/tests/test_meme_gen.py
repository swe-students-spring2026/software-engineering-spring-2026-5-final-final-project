"""tests for meme generation functions."""

from app.logic.meme_gen import make_caption, make_file_name, pick_template


def test_pick_template_default():
    """check default template."""
    assert pick_template("random news") == "default.jpg"


def test_pick_template_money():
    """check template for economy-related text (i dunno man)."""
    assert pick_template("economy is bad") == "drake.jpg"


def test_pick_template_politics():
    """check template for politics-related text."""
    assert pick_template("politics today") == "distracted.jpg"


def test_make_caption_empty():
    """check caption when summary is empty."""
    result = make_caption("")
    assert result["top"] == "no summary"
    assert result["bottom"] == "cannot make meme"


def test_make_caption_fake():
    """check normal caption output."""
    result = make_caption("some summary")
    assert result["top"] == "when you read the news"
    assert result["bottom"] == "and it gets worse"


def test_make_file_name():
    """check file name format."""
    assert make_file_name("123") == "meme_123.png"
