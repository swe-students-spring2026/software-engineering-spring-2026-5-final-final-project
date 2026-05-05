"""Cat Can Token rules.

The token economy is kitten-only. Cats never earn, spend, hold, or lose
tokens. All mutating token paths must funnel through `grant_tokens` /
`spend_tokens` so the role check is centralized.
"""

from __future__ import annotations

from app.db.repository import Repository


class TokensNotPermitted(Exception):
    """Raised when a non-kitten role tries to participate in token flow."""


def is_kitten(repository: Repository, user_id: str) -> bool:
    return repository.get_user_role(user_id) == "kitten"


def require_kitten(repository: Repository, user_id: str) -> None:
    if not is_kitten(repository, user_id):
        raise TokensNotPermitted(
            f"user '{user_id}' is not a kitten; cats do not participate in tokens"
        )


def get_balance(repository: Repository, user_id: str) -> int:
    """Cats always read 0; kittens read whatever the repo holds."""

    if not is_kitten(repository, user_id):
        return 0
    return repository.get_tokens(user_id)


def grant_tokens(repository: Repository, user_id: str, amount: int) -> int:
    """Award tokens to a kitten. Cats are silently ignored (no-op, returns 0)."""

    if amount < 0:
        raise ValueError("grant_tokens amount must be non-negative; use spend_tokens")
    if not is_kitten(repository, user_id):
        return 0
    return repository.add_tokens(user_id, amount)


def spend_tokens(repository: Repository, user_id: str, amount: int) -> int:
    """Deduct tokens from a kitten. Refuses cats and overdrafts."""

    if amount < 0:
        raise ValueError("spend_tokens amount must be non-negative")
    require_kitten(repository, user_id)
    current = repository.get_tokens(user_id)
    if current < amount:
        raise ValueError("insufficient tokens")
    return repository.add_tokens(user_id, -amount)


def deduct_for_failed_attempt(repository: Repository, user_id: str) -> int:
    """Cat-can-token loss when a kitten exhausts the 5-attempt limit.

    Always docks 1 token from a kitten (balance may go negative — that's
    deliberate, since the loss is a quiz-system penalty, not a transaction).
    Cats are skipped — they don't participate in the token economy.
    Returns the new balance.
    """

    if not is_kitten(repository, user_id):
        return repository.get_tokens(user_id)
    return repository.add_tokens(user_id, -1)
