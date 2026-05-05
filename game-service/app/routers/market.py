"""Marketplace routes for kitten-to-kitten fish trades.

Cats are blocked from every mutating endpoint here — the marketplace runs
purely on Cat Can Tokens, and cats don't have a balance.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import get_repository
from app.db.repository import Repository
from app.models import (
    BuyListingRequest,
    CreateListingRequest,
    MarketListing,
    MarketListingResponse,
)
from app.services import tokens as token_service

router = APIRouter(prefix="/market", tags=["market"])


def repo() -> Repository:
    """Return the configured game repository."""

    return get_repository()


def _require_kitten(repository: Repository, user_id: str, action: str) -> None:
    if not token_service.is_kitten(repository, user_id):
        raise HTTPException(
            status_code=403,
            detail=f"cats cannot {action}; the marketplace is kitten-only",
        )


@router.get("/health")
async def health():
    """Return marketplace health."""

    return {"status": "market ok"}


@router.get("/listings", response_model=List[MarketListing])
async def list_listings(
    rarity: Optional[str] = Query(default=None),
    species_id: Optional[str] = Query(default=None),
    min_price: Optional[int] = Query(default=None, ge=0),
    max_price: Optional[int] = Query(default=None, ge=0),
    sort_by: str = Query(
        default="newest",
        pattern="^(newest|price_asc|price_desc|rarity)$",
    ),
    repository: Repository = Depends(repo),
):
    """Return active fish marketplace listings, optionally filtered/sorted."""

    listings = repository.list_market_listings(
        rarity=rarity,
        species_id=species_id,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
    )
    return [MarketListing(**listing) for listing in listings]


@router.post("/list", response_model=MarketListingResponse)
async def create_listing(
    payload: CreateListingRequest,
    repository: Repository = Depends(repo),
):
    """List a marketplace-eligible fish for Cat Can Tokens."""

    _require_kitten(repository, payload.user_id, "list fish")
    try:
        listing = repository.create_market_listing(
            user_id=payload.user_id,
            fish_id=payload.fish_id,
            price=payload.price,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return MarketListingResponse(
        listing=MarketListing(**listing),
        seller_tokens=repository.get_tokens(payload.user_id),
    )


@router.post("/buy/{listing_id}", response_model=MarketListingResponse)
async def buy_listing(
    listing_id: str,
    payload: BuyListingRequest,
    repository: Repository = Depends(repo),
):
    """Buy an active market listing and transfer fish ownership."""

    _require_kitten(repository, payload.buyer_id, "buy fish")
    try:
        listing = repository.buy_market_listing(
            listing_id=listing_id,
            buyer_id=payload.buyer_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return MarketListingResponse(
        listing=MarketListing(**listing),
        seller_tokens=repository.get_tokens(listing["seller_id"]),
        buyer_tokens=repository.get_tokens(payload.buyer_id),
    )


@router.delete("/listings/{listing_id}", response_model=MarketListing)
async def unlist_listing(
    listing_id: str,
    seller_id: str = Query(...),
    repository: Repository = Depends(repo),
):
    """Cancel an active listing. Only the original seller may do this."""

    _require_kitten(repository, seller_id, "unlist fish")
    try:
        listing = repository.unlist_market_listing(
            listing_id=listing_id,
            seller_id=seller_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MarketListing(**listing)
