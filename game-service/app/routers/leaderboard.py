"""Leaderboard routes for token and aquarium collection rankings."""

from fastapi import APIRouter, Depends

from app.db import get_repository
from app.db.repository import Repository
from app.models import AquariumLeaderboardEntry, TokenLeaderboardEntry

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


def repo() -> Repository:
    """Return the configured game repository."""

    return get_repository()


def aquarium_score(user_id: str, repository: Repository) -> AquariumLeaderboardEntry:
    """Compute a user's aquarium leaderboard row."""

    profile = repository.get_user_profile(user_id) or {}
    inventory = repository.get_inventory(user_id)
    total_species = len(repository.list_fish_species())
    collected_species = len({fish["species_id"] for fish in inventory})
    percentage = (
        round((collected_species / total_species) * 100, 2) if total_species else 0.0
    )
    return AquariumLeaderboardEntry(
        user_id=user_id,
        username=profile.get("username", user_id),
        collected_species=collected_species,
        total_species=total_species,
        collection_percentage=percentage,
    )


@router.get("/tokens", response_model=list[TokenLeaderboardEntry])
async def token_leaderboard(
    limit: int = 10,
    repository: Repository = Depends(repo),
):
    """Return kittens ranked by Cat Can Token balance. Cats are excluded."""

    balances = repository.list_token_balances()
    kitten_balances = [
        entry
        for entry in balances
        if repository.get_user_role(entry["user_id"]) == "kitten"
    ]
    leaders = sorted(
        kitten_balances,
        key=lambda entry: entry["tokens"],
        reverse=True,
    )[:limit]
    return [
        TokenLeaderboardEntry(
            user_id=entry["user_id"],
            username=(repository.get_user_profile(entry["user_id"]) or {}).get(
                "username",
                entry["user_id"],
            ),
            tokens=entry["tokens"],
        )
        for entry in leaders
    ]


@router.get("/aquarium", response_model=list[AquariumLeaderboardEntry])
async def aquarium_leaderboard(
    limit: int = 10,
    repository: Repository = Depends(repo),
):
    """Return kittens ranked by unique fish species collected."""

    user_ids = {entry["user_id"] for entry in repository.list_token_balances()}
    user_ids.update(repository.list_inventory_user_ids())
    rows = [aquarium_score(user_id, repository) for user_id in user_ids]
    return sorted(
        rows,
        key=lambda row: (row.collection_percentage, row.collected_species),
        reverse=True,
    )[:limit]
