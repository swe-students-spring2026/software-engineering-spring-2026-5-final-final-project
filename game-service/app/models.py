from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ProblemSummary(BaseModel):
    """Public-facing problem listing entry. No starter / test code exposed."""

    id: str
    title: str
    difficulty: str
    fishing_reward: int
    completed: bool = False
    exhausted: bool = False
    attempts_used: int = 0


class Problem(BaseModel):
    """Full problem detail. Test code stays server-side, never returned."""

    id: str
    title: str
    function_name: str
    instructions: str
    starter_code: str
    difficulty: str
    fishing_reward: int
    source: str
    source_url: str
    max_attempts: int = 5


class SubmitRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=10_000)
    language: str = "python"
    # phase 1: hardcoded. once auth-service is wired up, this comes from JWT.
    user_id: str = "demo_user"


class SubmitResponse(BaseModel):
    passed: bool
    tests_run: int
    tests_passed: int
    failed_test: Optional[str] = None
    error_message: Optional[str] = None
    fishing_reward_granted: int = 0
    new_fishing_chances: Optional[int] = None
    attempts_used: int = 0
    attempts_remaining: int = 5
    max_attempts: int = 5
    solution_revealed: bool = False
    solution_code: Optional[str] = None
    added_to_uncaught_fish: bool = False
    tokens_lost: int = 0


class UncaughtProblem(BaseModel):
    """Problem saved after a kitten exhausts all attempts."""

    user_id: str
    problem_id: str
    title: str
    solution_code: str
    solution_explanation: Optional[str] = None
    attempts_used: int


# --- Fishing ---


class Rarity(str, Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class Quality(str, Enum):
    NORMAL = "normal"
    SHINY = "shiny"
    PERFECT = "perfect"


class FishSpecies(BaseModel):
    """Static metadata for a fish species. Many instances share these."""

    id: str
    species_id: str
    name: str
    species: str
    rarity: Rarity
    catch_probability: float
    image_url: str
    image_path: str
    animation_url: Optional[str] = None
    description: str
    sell_value: int
    sell_value_tokens: int
    marketplace_eligible: bool
    is_system_sellable: bool = False
    base_price: int
    typical_size_cm: float
    image_pool: List[str]


class InventoryFish(BaseModel):
    """A specific fish a user owns. fish_id is what market and sell-small reference."""

    fish_id: str
    species_id: str
    species_name: str
    species: str
    rarity: Rarity
    quality: Quality
    size_cm: float
    weight_g: float
    image_url: str
    image_path: str
    description: str
    caught_at: datetime
    suggested_price: int
    sell_value: int
    sell_value_tokens: int
    marketplace_eligible: bool
    is_system_sellable: bool = False
    is_small: bool


class CastResponse(BaseModel):
    fish: InventoryFish
    remaining_chances: int


class InventoryResponse(BaseModel):
    user_id: str
    fish: List[InventoryFish]
    total_count: int
    tokens: int
    fishing_chances: int


class SellSmallResponse(BaseModel):
    fish_id: str
    species_id: str
    tokens_earned: int
    new_token_balance: int


# --- Marketplace, Aquarium, Leaderboards ---


class MarketListing(BaseModel):
    """A fish listed for kitten-to-kitten purchase."""

    listing_id: str
    seller_id: str
    fish: InventoryFish
    price: int
    status: str


class CreateListingRequest(BaseModel):
    """Request body for listing a fish on the marketplace."""

    user_id: str = "demo_user"
    fish_id: str
    price: int = Field(..., gt=0)


class BuyListingRequest(BaseModel):
    """Request body for buying a marketplace listing."""

    buyer_id: str


class MarketListingResponse(BaseModel):
    """Response returned after a market listing changes state."""

    listing: MarketListing
    seller_tokens: Optional[int] = None
    buyer_tokens: Optional[int] = None


class AquariumSpecies(BaseModel):
    """Aggregated aquarium collection row for one fish species."""

    species_id: str
    species_name: str
    rarity: Rarity
    quantity: int
    image_url: str
    description: str


class AquariumResponse(BaseModel):
    """A kitten's aquarium progress and collected species."""

    user_id: str
    collected_species: int
    total_species: int
    collection_percentage: float
    fish: List[AquariumSpecies]


class TokenLeaderboardEntry(BaseModel):
    """Token leaderboard row."""

    user_id: str
    username: str = ""
    tokens: int


class AquariumLeaderboardEntry(BaseModel):
    """Aquarium collection leaderboard row."""

    user_id: str
    username: str = ""
    collected_species: int
    total_species: int
    collection_percentage: float
