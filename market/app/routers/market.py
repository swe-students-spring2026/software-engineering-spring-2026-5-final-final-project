"""Marketplace router for local module tests.

The production route lives in `game-service/app/routers/market.py`. This module
keeps the market folder executable and mirrors the same route contract.
"""

from __future__ import annotations

from typing import Literal
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(prefix="/market", tags=["market"])


class Fish(BaseModel):
    """Market fish record."""

    fish_id: str
    species_id: str
    species_name: str
    rarity: str
    marketplace_eligible: bool = True


class Listing(BaseModel):
    """Marketplace listing record."""

    listing_id: str
    seller_id: str
    fish: Fish
    price: int
    status: Literal["active", "sold", "cancelled"] = "active"
    buyer_id: str | None = None


class CreateListingRequest(BaseModel):
    """Create listing request."""

    seller_id: str
    fish: Fish
    price: int = Field(gt=0)


class BuyListingRequest(BaseModel):
    """Buy listing request."""

    buyer_id: str
    buyer_tokens: int = Field(ge=0)


listings: dict[str, Listing] = {}


@router.get("/health")
async def health():
    """Return module health."""

    return {"status": "market ok"}


@router.get("/listings", response_model=list[Listing])
async def list_marketings():
    """Return active market listings."""

    return [listing for listing in listings.values() if listing.status == "active"]


@router.post("/list", response_model=Listing)
async def create_listing(payload: CreateListingRequest):
    """Create a listing for a marketplace-eligible fish."""

    if not payload.fish.marketplace_eligible:
        raise HTTPException(status_code=400, detail="fish is not marketplace eligible")
    listing = Listing(
        listing_id=str(uuid.uuid4()),
        seller_id=payload.seller_id,
        fish=payload.fish,
        price=payload.price,
    )
    listings[listing.listing_id] = listing
    return listing


@router.post("/buy/{listing_id}", response_model=Listing)
async def buy_listing(listing_id: str, payload: BuyListingRequest):
    """Buy an active listing with Cat Can Tokens."""

    listing = listings.get(listing_id)
    if listing is None or listing.status != "active":
        raise HTTPException(status_code=404, detail="listing not found")
    if listing.seller_id == payload.buyer_id:
        raise HTTPException(status_code=400, detail="buyer cannot be seller")
    if payload.buyer_tokens < listing.price:
        raise HTTPException(status_code=400, detail="insufficient tokens")
    listing.status = "sold"
    listing.buyer_id = payload.buyer_id
    return listing
