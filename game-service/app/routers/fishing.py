"""Fishing module: card-draw + inventory + small-fish refund.

Each cast costs 1 fishing chance (earned by passing quiz problems) and
produces a unique fish instance. Same species can yield different sizes,
qualities, and images, so two trout in the same inventory are distinct.

Sell-small refunds tokens for fish below the species' typical size.
Larger fish are meant for the market module (Meili) — this router only
handles refunds, not P2P trades.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.db import get_repository
from app.db.repository import Repository
from app.models import (
    CastResponse,
    FishSpecies,
    InventoryFish,
    InventoryResponse,
    Quality,
    Rarity,
    SellSmallResponse,
)
from app.services import tokens as token_service

router = APIRouter(prefix="/fishing", tags=["fishing"])


def repo() -> Repository:
    return get_repository()


# --- tunables ---

RARITY_DRAW_WEIGHTS = {
    Rarity.COMMON.value: 60.0,
    Rarity.UNCOMMON.value: 25.0,
    Rarity.RARE.value: 10.0,
    Rarity.EPIC.value: 4.0,
    Rarity.LEGENDARY.value: 1.0,
}

QUALITY_DRAW_WEIGHTS = {
    Quality.NORMAL.value: 95.0,
    Quality.SHINY.value: 4.5,
    Quality.PERFECT.value: 0.5,
}

QUALITY_PRICE_MULTIPLIER = {
    Quality.NORMAL.value: 1.0,
    Quality.SHINY.value: 2.0,
    Quality.PERFECT.value: 5.0,
}
MARKET_RARITIES = {
    Rarity.UNCOMMON.value,
    Rarity.RARE.value,
    Rarity.EPIC.value,
    Rarity.LEGENDARY.value,
}

# Small-fish refund returns a fraction of suggested_price. Bigger payouts
# come from the market.
SMALL_FISH_REFUND_RATIO = 0.5
DEMO_MARKET_STARTER_TOKENS = 300
STARTER_LIONFISH_FLAG = "starter_lionfish_granted"
STARTER_LIONFISH_SPECIES_ID = "lionfish"

# size ~ N(typical, typical * SIZE_SIGMA_FACTOR), clamped to a sane range.
SIZE_SIGMA_FACTOR = 0.30
SIZE_MIN_FACTOR = 0.30
SIZE_MAX_FACTOR = 2.50

# weight (g) ≈ WEIGHT_K * size_cm^3. Order-of-magnitude heuristic.
WEIGHT_K = 12.0


# --- helpers ---


def _roll_size_cm(typical_cm: float, rng: random.Random) -> float:
    sigma = typical_cm * SIZE_SIGMA_FACTOR
    raw = rng.gauss(typical_cm, sigma)
    lo = typical_cm * SIZE_MIN_FACTOR
    hi = typical_cm * SIZE_MAX_FACTOR
    return max(lo, min(hi, raw))


def _roll_quality(rng: random.Random) -> str:
    qualities = list(QUALITY_DRAW_WEIGHTS.keys())
    weights = list(QUALITY_DRAW_WEIGHTS.values())
    return rng.choices(qualities, weights=weights, k=1)[0]


def _pick_species(species_list: list[dict], rng: random.Random) -> dict:
    weights = [
        float(s.get("catch_probability") or RARITY_DRAW_WEIGHTS.get(s["rarity"], 1.0))
        for s in species_list
    ]
    return rng.choices(species_list, weights=weights, k=1)[0]


def _compute_suggested_price(
    base_price: int, size_cm: float, typical_cm: float, quality: str
) -> int:
    size_ratio = size_cm / typical_cm if typical_cm > 0 else 1.0
    multiplier = QUALITY_PRICE_MULTIPLIER[quality]
    return max(1, int(round(base_price * size_ratio * multiplier)))


def _build_fish(species: dict, rng: random.Random) -> dict:
    typical = float(species.get("typical_size_cm", 30.0))
    size_cm = _roll_size_cm(typical, rng)
    quality = _roll_quality(rng)
    weight_g = WEIGHT_K * (size_cm**3) / 1000.0  # rough, in grams
    image_pool = species.get("image_pool") or []
    image_url = rng.choice(image_pool) if image_pool else ""
    sell_value = int(species.get("sell_value", species["base_price"]))
    rarity = species["rarity"]
    marketplace_eligible = rarity in MARKET_RARITIES
    is_system_sellable = rarity == Rarity.COMMON.value

    return {
        "fish_id": str(uuid.uuid4()),
        "species_id": species["id"],
        "species_name": species["name"],
        "species": species.get("species", species["name"]),
        "rarity": rarity,
        "quality": quality,
        "size_cm": round(size_cm, 1),
        "weight_g": round(weight_g, 1),
        "image_url": image_url,
        "image_path": image_url,
        "description": species.get("description", ""),
        "caught_at": datetime.now(timezone.utc).isoformat(),
        "suggested_price": _compute_suggested_price(
            base_price=sell_value,
            size_cm=size_cm,
            typical_cm=typical,
            quality=quality,
        ),
        "sell_value": sell_value,
        "sell_value_tokens": sell_value,
        "marketplace_eligible": marketplace_eligible,
        "is_system_sellable": is_system_sellable,
        "is_small": size_cm < typical,
    }


def _starter_lionfish_id(user_id: str) -> str:
    safe_user_id = "".join(ch if ch.isalnum() else "_" for ch in user_id)
    return f"starter_lionfish_{safe_user_id}"


def _pick_lionfish_species(repository: Repository) -> dict | None:
    species = repository.get_fish_species(STARTER_LIONFISH_SPECIES_ID)
    if species is not None:
        return species
    for candidate in repository.list_fish_species():
        if candidate.get("name") == "Lionfish":
            return candidate
    return None


def _build_starter_lionfish(user_id: str, species: dict) -> dict:
    fish = _build_fish(species, random.Random(f"starter-lionfish:{user_id}"))
    fish["fish_id"] = _starter_lionfish_id(user_id)
    fish["quality"] = Quality.NORMAL.value
    fish["size_cm"] = float(species.get("typical_size_cm", fish["size_cm"]))
    fish["suggested_price"] = int(species.get("base_price", species["sell_value"]))
    fish["marketplace_eligible"] = True
    fish["is_system_sellable"] = False
    fish["is_small"] = False
    return fish


def _ensure_starter_lionfish(user_id: str, repository: Repository) -> None:
    if not user_id.startswith("kitten_"):
        return
    if not token_service.is_kitten(repository, user_id):
        return
    if repository.get_user_flag(user_id, STARTER_LIONFISH_FLAG):
        return

    species = _pick_lionfish_species(repository)
    if species is None:
        return
    repository.add_fish_to_inventory(
        user_id,
        _build_starter_lionfish(user_id, species),
    )
    if repository.get_tokens(user_id) < DEMO_MARKET_STARTER_TOKENS:
        repository.add_tokens(
            user_id,
            DEMO_MARKET_STARTER_TOKENS - repository.get_tokens(user_id),
        )
    repository.set_user_flag(user_id, STARTER_LIONFISH_FLAG, True)


def _inventory_response(user_id: str, repository: Repository) -> InventoryResponse:
    fish = repository.get_inventory(user_id)
    return InventoryResponse(
        user_id=user_id,
        fish=[InventoryFish(**f) for f in fish],
        total_count=len(fish),
        tokens=repository.get_tokens(user_id),
        fishing_chances=repository.get_fishing_chances(user_id),
    )


# --- endpoints ---


@router.get("/species", response_model=List[FishSpecies])
async def list_species(repository: Repository = Depends(repo)):
    return [FishSpecies(**s) for s in repository.list_fish_species()]


@router.post("/cast", response_model=CastResponse)
async def cast(
    user_id: str = "demo_user",
    repository: Repository = Depends(repo),
):
    species_list = repository.list_fish_species()
    if not species_list:
        raise HTTPException(
            status_code=503,
            detail="fish dataset is empty; run scripts/build_fish_catalog.py",
        )

    try:
        remaining = repository.consume_fishing_chance(user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="no fishing chances; pass quiz problems to earn more",
        ) from exc

    rng = random.Random()
    species = _pick_species(species_list, rng)
    fish = _build_fish(species, rng)
    repository.add_fish_to_inventory(user_id, fish)

    return CastResponse(
        fish=InventoryFish(**fish),
        remaining_chances=remaining,
    )


@router.get("/inventory/{user_id}", response_model=InventoryResponse)
async def get_inventory(user_id: str, repository: Repository = Depends(repo)):
    _ensure_starter_lionfish(user_id, repository)
    return _inventory_response(user_id, repository)


@router.post("/starter-lionfish/{user_id}", response_model=InventoryResponse)
async def grant_starter_lionfish(
    user_id: str,
    repository: Repository = Depends(repo),
):
    """Give a kitten their one-time Lionfish starter for the aquarium."""

    if not token_service.is_kitten(repository, user_id):
        raise HTTPException(
            status_code=403,
            detail="cats do not participate in the token economy",
        )
    _ensure_starter_lionfish(user_id, repository)
    return _inventory_response(user_id, repository)


@router.post("/demo-market-starter/{user_id}", response_model=InventoryResponse)
async def grant_demo_market_starter(
    user_id: str,
    repository: Repository = Depends(repo),
):
    """Backward-compatible alias for the Lionfish starter endpoint."""

    return await grant_starter_lionfish(user_id, repository)


@router.post("/sell-small/{fish_id}", response_model=SellSmallResponse)
async def sell_small(
    fish_id: str,
    user_id: str = "demo_user",
    repository: Repository = Depends(repo),
):
    if not token_service.is_kitten(repository, user_id):
        raise HTTPException(
            status_code=403,
            detail="cats do not participate in the token economy",
        )
    fish = repository.get_fish(user_id, fish_id)
    if fish is None:
        raise HTTPException(
            status_code=404,
            detail=f"fish '{fish_id}' not found in {user_id}'s inventory",
        )
    if fish.get("marketplace_eligible", False):
        raise HTTPException(
            status_code=400,
            detail="this fish is marketplace eligible; list it with other kittens instead",
        )
    if not fish.get("is_small", False):
        raise HTTPException(
            status_code=400,
            detail="this fish is not small; list it on the market instead",
        )

    refund = max(1, int(round(fish["suggested_price"] * SMALL_FISH_REFUND_RATIO)))
    removed = repository.remove_fish_from_inventory(user_id, fish_id)
    if removed is None:
        # Race: someone removed it between get_fish and remove. Refuse.
        raise HTTPException(
            status_code=409,
            detail="fish was removed concurrently; please retry",
        )
    new_balance = token_service.grant_tokens(repository, user_id, refund)

    return SellSmallResponse(
        fish_id=fish_id,
        species_id=fish["species_id"],
        tokens_earned=refund,
        new_token_balance=new_balance,
    )


@router.post("/sell/{fish_id}", response_model=SellSmallResponse)
async def sell_to_system(
    fish_id: str,
    user_id: str = "demo_user",
    repository: Repository = Depends(repo),
):
    """Direct system sale of a common fish.

    Uncommon, rare, epic, and legendary fish are blocked here — they must go
    through the kitten-to-kitten marketplace. Cats are blocked outright.
    """

    if not token_service.is_kitten(repository, user_id):
        raise HTTPException(
            status_code=403,
            detail="cats do not participate in the token economy",
        )
    fish = repository.get_fish(user_id, fish_id)
    if fish is None:
        raise HTTPException(
            status_code=404,
            detail=f"fish '{fish_id}' not found in {user_id}'s inventory",
        )
    if fish.get("rarity") != Rarity.COMMON.value:
        raise HTTPException(
            status_code=400,
            detail=(
                "only common fish can be sold directly; "
                "list uncommon or rarer fish on the marketplace instead"
            ),
        )

    payout = max(1, int(fish.get("sell_value_tokens", fish.get("sell_value", 1))))
    removed = repository.remove_fish_from_inventory(user_id, fish_id)
    if removed is None:
        raise HTTPException(
            status_code=409,
            detail="fish was removed concurrently; please retry",
        )
    new_balance = token_service.grant_tokens(repository, user_id, payout)

    return SellSmallResponse(
        fish_id=fish_id,
        species_id=fish["species_id"],
        tokens_earned=payout,
        new_token_balance=new_balance,
    )
