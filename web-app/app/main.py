"""Small presentation helpers for the web app."""


def health():
    """Return web app health status."""
    return {"status": "ok"}


def home_text():
    """Return home page text."""
    return "News2Meme"


def result_text(summary, image):
    """Return result text."""
    if summary == "" or image == "":
        return "missing result"

    return "summary: " + summary + " image: " + image
