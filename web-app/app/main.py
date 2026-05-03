"""main web app file base (ok to change)."""


def health():
    """return web app health status."""
    return {"status": "ok"}


def home_text():
    """return home page text."""
    return "News2Meme"


def result_text(summary, image):
    """return result text."""
    if summary == "" or image == "":
        return "missing result"

    return "summary: " + summary + " image: " + image
