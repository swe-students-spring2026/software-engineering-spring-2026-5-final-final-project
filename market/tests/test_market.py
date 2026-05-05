"""Tests for the standalone market module."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from market.app.routers.market import listings, router


app = FastAPI()
app.include_router(router)
client = TestClient(app)


def setup_function():
    """Reset in-memory listings for each test."""

    listings.clear()


def test_health():
    """Market health endpoint is available."""

    response = client.get("/market/health")
    assert response.status_code == 200
    assert response.json()["status"] == "market ok"


def test_create_and_buy_listing():
    """A marketplace-eligible fish can be listed and bought."""

    created = client.post(
        "/market/list",
        json={
            "seller_id": "seller",
            "price": 20,
            "fish": {
                "fish_id": "fish-1",
                "species_id": "bluefin_tuna",
                "species_name": "Bluefin Tuna",
                "rarity": "rare",
                "marketplace_eligible": True,
            },
        },
    )
    assert created.status_code == 200
    listing_id = created.json()["listing_id"]

    bought = client.post(
        f"/market/buy/{listing_id}",
        json={"buyer_id": "buyer", "buyer_tokens": 30},
    )
    assert bought.status_code == 200
    assert bought.json()["status"] == "sold"
