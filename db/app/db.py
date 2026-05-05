"""simple database helper functions. (feel free to change)"""


def make_meme_record(url, summary, image):
    """create a fake database."""
    if url == "":
        raise ValueError("url is missing")

    return {
        "url": url,
        "summary": summary,
        "image": image,
    }


def is_valid_record(record):
    """check if record has required fields."""
    return "url" in record and "summary" in record and "image" in record
