"""simple ML logic (fake for now)."""


def predict(text):
    """return fake prediction."""
    if text == "":
        return "no input"

    if "bad" in text:
        return "negative"

    return "positive"
