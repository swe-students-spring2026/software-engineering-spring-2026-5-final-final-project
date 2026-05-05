"""main backend app file."""

from app.logic.scraper import get_article
from app.logic.sum import make_summary
from app.logic.meme_gen import make_caption, make_file_name, pick_template
from app.logic.storage import make_doc


def health():
    """health status."""
    return {"status": "ok"}


def make_meme(url):
    """make meme data from a news URL."""
    if url == "":
        raise ValueError("url is missing")

    article = get_article(url)
    summary = make_summary(article)
    caption = make_caption(summary)
    pick_template(summary)
    image = make_file_name("1")

    return make_doc(url, summary, caption["top"], caption["bottom"], image)
