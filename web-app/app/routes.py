"""route helper functions."""


def check_url(url):
    """check if a URL was given."""
    if url == "":
        return False

    return True


def make_request_data(url):
    """make request data for backend."""
    if url == "":
        raise ValueError("url is missing")

    return {"url": url}


def show_error(message):
    """return error message."""
    return "error: " + message
