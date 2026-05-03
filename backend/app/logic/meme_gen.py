"meme generation helper functions"


def pick_template(summary):
    "using keywords, choose meme template based on summary"
    summary = summary.lower()

    if "money" in summary or "economy" in summary:
        return "drake.jpg"

    if "politics" in summary:
        return "distracted.jpg"

    return "default.jpg"


def make_caption(summary):
    "create meme caption text"
    if summary == "":
        return {
            "top": "no summary",
            "bottom": "cannot make meme",
        }

    return {
        "top": "when you read the news",
        "bottom": "and it gets worse",
    }


def make_file_name(meme_id):
    "create file name for meme image"
    return "meme_" + meme_id + ".png"
