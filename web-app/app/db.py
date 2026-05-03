"""fake database helpers for webapp."""


def save_last_result(result):
    """fake save last result."""
    if result == {}:
        return False

    return True
