"""Cat Can Token read endpoints.

Token mutations live with the action that triggered them (quiz failure,
fishing system-sell, market purchase). This router only exposes balance
and role-aware status reads.
"""

from fastapi import APIRouter, Depends

from app.db import get_repository
from app.db.repository import Repository
from app.services import tokens as token_service

router = APIRouter(prefix="/tokens", tags=["tokens"])


def repo() -> Repository:
    return get_repository()


@router.get("/{user_id}")
async def get_balance(user_id: str, repository: Repository = Depends(repo)):
    """Return a user's Cat Can Token balance plus their participation status."""

    role = repository.get_user_role(user_id)
    enabled = role == "kitten"
    return {
        "user_id": user_id,
        "role": role,
        "tokens": token_service.get_balance(repository, user_id),
        "token_system_enabled": enabled,
    }
