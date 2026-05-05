"""Aquarium routes for collection progress."""

from collections import Counter

from fastapi import APIRouter, Depends

from app.db import get_repository
from app.db.repository import Repository
from app.models import AquariumResponse, AquariumSpecies

router = APIRouter(prefix="/aquarium", tags=["aquarium"])


def repo() -> Repository:
    """Return the configured game repository."""

    return get_repository()


@router.get("/health")
async def health():
    """Return aquarium health."""

    return {"status": "aquarium ok"}


@router.get("/{user_id}", response_model=AquariumResponse)
async def get_aquarium(user_id: str, repository: Repository = Depends(repo)):
    """Return unique-species collection progress for a kitten."""

    inventory = repository.get_inventory(user_id)
    species_by_id = {
        species["id"]: species for species in repository.list_fish_species()
    }
    quantities = Counter(fish["species_id"] for fish in inventory)
    collected = []

    for species_id, quantity in sorted(quantities.items()):
        species = species_by_id.get(species_id)
        if species is None:
            continue
        collected.append(
            AquariumSpecies(
                species_id=species_id,
                species_name=species["name"],
                rarity=species["rarity"],
                quantity=quantity,
                image_url=species["image_url"],
                description=species["description"],
            )
        )

    total_species = len(species_by_id)
    collected_species = len(collected)
    percentage = (
        round((collected_species / total_species) * 100, 2) if total_species else 0.0
    )

    return AquariumResponse(
        user_id=user_id,
        collected_species=collected_species,
        total_species=total_species,
        collection_percentage=percentage,
        fish=collected,
    )
