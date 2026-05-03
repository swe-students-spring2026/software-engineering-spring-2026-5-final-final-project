"""Teacher-service helper contracts.

This module is intentionally small for now. It keeps teacher-facing payload
rules in one place without introducing a separate persistence layer.
"""

MAX_PROBLEMS_PER_POND = 100


def teacher_token_policy() -> dict:
    """Return the token policy for CatCh teacher users."""

    return {
        "role": "cat",
        "token_system_enabled": False,
        "can_buy_fish": False,
        "can_sell_fish": False,
        "included_in_token_leaderboard": False,
        "included_in_aquarium_leaderboard": False,
    }


def validate_problem_count(problem_ids: list[str]) -> bool:
    """Return whether a problem list fits within the pond limit."""

    return len(problem_ids) <= MAX_PROBLEMS_PER_POND
