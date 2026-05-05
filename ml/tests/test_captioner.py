"""Tests for meme caption generation."""

from meme.captioner import (
    MemeCaption,
    generate_caption,
    heuristic_caption,
    normalize_text,
    shorten,
)


def test_normalize_text_collapses_whitespace():
    """Check whitespace normalization."""
    assert normalize_text(" one\n\n two\tthree ") == "one two three"


def test_shorten_keeps_short_text():
    """Check short text is unchanged."""
    assert shorten("short text", 20) == "short text"


def test_shorten_clips_at_word_boundary():
    """Check long text is shortened cleanly."""
    assert shorten("one two three four five", 14) == "one two…"


def test_shorten_clips_long_single_word():
    """Check long words still shorten."""
    assert shorten("supercalifragilistic", 8) == "superca…"


def test_heuristic_caption_empty_text():
    """Check empty text fallback."""
    assert heuristic_caption("   ") == MemeCaption(
        top="No article text",
        bottom="No meme today",
    )


def test_heuristic_caption_two_sentences():
    """Check sentence split captioning."""
    assert heuristic_caption("First sentence. Second sentence.") == MemeCaption(
        top="First sentence.",
        bottom="Second sentence.",
    )


def test_heuristic_caption_short_text():
    """Check short text fallback."""
    assert heuristic_caption("short article") == MemeCaption(
        top="short article",
        bottom="me acting informed",
    )


def test_heuristic_caption_long_text():
    """Check long text split."""
    assert heuristic_caption("one two three four five six seven eight") == MemeCaption(
        top="one two three four",
        bottom="five six seven eight",
    )


def test_generate_caption_uses_heuristic():
    """Check public caption generator."""
    assert generate_caption("short article", use_ai=True) == MemeCaption(
        top="short article",
        bottom="me acting informed",
    )
