"""scraping helper functions."""


def clean_text(text):
    """clean article text by removing unnessecary whitespace."""
    if text == "":
        return ""

    words = text.split()
    return " ".join(words)


def get_article(url):
    """temp fake scraper."""
    if url == "":
        raise ValueError("url is missing")

    return "fake article text"
