"""Tests for the kitten-only token economy, sell rules, marketplace, and leaderboard."""

from datetime import datetime, timezone

from app.db.mock_repo import MockRepository


def _fish(
    fish_id: str,
    species_id: str = "bluefin_tuna",
    rarity: str = "rare",
    marketplace_eligible: bool = True,
    is_system_sellable: bool = False,
    sell_value: int = 70,
) -> dict:
    return {
        "fish_id": fish_id,
        "species_id": species_id,
        "species_name": species_id.replace("_", " ").title(),
        "species": species_id,
        "rarity": rarity,
        "quality": "normal",
        "size_cm": 120.0,
        "weight_g": 18000.0,
        "image_url": f"/fish_images/{species_id}.png",
        "image_path": f"/fish_images/{species_id}.png",
        "description": "test fish",
        "caught_at": datetime.now(timezone.utc).isoformat(),
        "suggested_price": sell_value,
        "sell_value": sell_value,
        "sell_value_tokens": sell_value,
        "marketplace_eligible": marketplace_eligible,
        "is_system_sellable": is_system_sellable,
        "is_small": False,
    }


def _common_fish(fish_id: str = "f-1") -> dict:
    return _fish(
        fish_id,
        species_id="pond_minnow",
        rarity="common",
        marketplace_eligible=False,
        is_system_sellable=True,
        sell_value=5,
    )


# ---------- Cat Can Token role enforcement ----------


def test_cat_balance_endpoint_reports_zero(client):
    repo = MockRepository.get_instance()
    repo.set_user_role("teacher_meow", "cat")

    response = client.get("/tokens/teacher_meow")
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "cat"
    assert body["tokens"] == 0
    assert body["token_system_enabled"] is False


def test_kitten_balance_endpoint_reports_balance(client):
    repo = MockRepository.get_instance()
    repo.add_tokens("kit-1", 12)

    response = client.get("/tokens/kit-1")
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "kitten"
    assert body["tokens"] == 12
    assert body["token_system_enabled"] is True


def test_token_service_grant_skips_cats():
    from app.services import tokens as token_service

    repo = MockRepository.get_instance()
    repo.set_user_role("cat-1", "cat")

    new_balance = token_service.grant_tokens(repo, "cat-1", 10)
    assert new_balance == 0
    assert repo.get_tokens("cat-1") == 0


def test_token_service_spend_refuses_cats():
    from app.services import tokens as token_service

    repo = MockRepository.get_instance()
    repo.set_user_role("cat-1", "cat")

    try:
        token_service.spend_tokens(repo, "cat-1", 1)
    except token_service.TokensNotPermitted:
        return
    assert False, "expected TokensNotPermitted"


# ---------- Fish selling rules ----------


def test_sell_low_rarity_to_system_pays_tokens(client):
    repo = MockRepository.get_instance()
    repo.add_fish_to_inventory("kit-1", _common_fish("f-common"))

    response = client.post("/fishing/sell/f-common?user_id=kit-1")
    assert response.status_code == 200
    body = response.json()
    assert body["tokens_earned"] == 5
    assert body["new_token_balance"] == 5
    assert repo.get_fish("kit-1", "f-common") is None


def test_sell_rare_fish_to_system_is_rejected(client):
    repo = MockRepository.get_instance()
    repo.add_fish_to_inventory("kit-1", _fish("f-rare"))

    response = client.post("/fishing/sell/f-rare?user_id=kit-1")
    assert response.status_code == 400
    assert "marketplace" in response.json()["detail"]
    assert repo.get_fish("kit-1", "f-rare") is not None


def test_cat_cannot_sell_to_system(client):
    repo = MockRepository.get_instance()
    repo.set_user_role("cat-1", "cat")
    repo.add_fish_to_inventory("cat-1", _common_fish("f-common"))

    response = client.post("/fishing/sell/f-common?user_id=cat-1")
    assert response.status_code == 403


# ---------- Marketplace ----------


def test_cat_cannot_list_fish(client):
    repo = MockRepository.get_instance()
    repo.set_user_role("cat-1", "cat")
    repo.add_fish_to_inventory("cat-1", _fish("f-rare"))

    response = client.post(
        "/market/list",
        json={"user_id": "cat-1", "fish_id": "f-rare", "price": 50},
    )
    assert response.status_code == 403


def test_cat_cannot_buy_fish(client):
    repo = MockRepository.get_instance()
    repo.add_fish_to_inventory("seller", _fish("f-rare"))
    repo.set_user_role("cat-buyer", "cat")

    listing = repo.create_market_listing("seller", "f-rare", 30)
    response = client.post(
        f"/market/buy/{listing['listing_id']}",
        json={"buyer_id": "cat-buyer"},
    )
    assert response.status_code == 403


def test_seller_can_unlist_their_listing(client):
    repo = MockRepository.get_instance()
    repo.add_fish_to_inventory("seller", _fish("f-rare"))
    listing = repo.create_market_listing("seller", "f-rare", 30)

    response = client.delete(
        f"/market/listings/{listing['listing_id']}?seller_id=seller"
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    # listing should disappear from active browse
    listings = client.get("/market/listings").json()
    assert all(l["listing_id"] != listing["listing_id"] for l in listings)


def test_non_seller_cannot_unlist(client):
    repo = MockRepository.get_instance()
    repo.add_fish_to_inventory("seller", _fish("f-rare"))
    listing = repo.create_market_listing("seller", "f-rare", 30)

    response = client.delete(
        f"/market/listings/{listing['listing_id']}?seller_id=other"
    )
    assert response.status_code == 400


def test_listings_filter_by_rarity_price_species(client):
    repo = MockRepository.get_instance()
    repo.add_fish_to_inventory("s1", _fish("f-1", species_id="bluefin_tuna", rarity="rare", sell_value=10))
    repo.add_fish_to_inventory("s1", _fish("f-2", species_id="great_white", rarity="legendary", sell_value=200))
    repo.add_fish_to_inventory("s1", _fish("f-3", species_id="bluefin_tuna", rarity="rare", sell_value=10))
    repo.create_market_listing("s1", "f-1", 20)
    repo.create_market_listing("s1", "f-2", 500)
    repo.create_market_listing("s1", "f-3", 80)

    rare_only = client.get("/market/listings?rarity=rare").json()
    assert len(rare_only) == 2
    assert all(l["fish"]["rarity"] == "rare" for l in rare_only)

    cheap_only = client.get("/market/listings?max_price=50").json()
    assert len(cheap_only) == 1
    assert cheap_only[0]["price"] == 20

    species_only = client.get("/market/listings?species_id=bluefin_tuna").json()
    assert len(species_only) == 2

    sorted_asc = client.get("/market/listings?sort_by=price_asc").json()
    assert [l["price"] for l in sorted_asc] == [20, 80, 500]


def test_buy_is_atomic_and_transfers_everything(client):
    repo = MockRepository.get_instance()
    repo.add_fish_to_inventory("seller", _fish("f-1"))
    repo.add_tokens("buyer", 100)

    listing = repo.create_market_listing("seller", "f-1", 40)
    response = client.post(
        f"/market/buy/{listing['listing_id']}",
        json={"buyer_id": "buyer"},
    )
    assert response.status_code == 200
    body = response.json()

    # buyer paid, seller earned
    assert body["buyer_tokens"] == 60
    assert body["seller_tokens"] == 40
    # fish moved
    assert repo.get_fish("buyer", "f-1") is not None
    assert repo.get_fish("seller", "f-1") is None
    # listing closed
    assert body["listing"]["status"] == "sold"


def test_buy_rejects_when_buyer_underfunded(client):
    repo = MockRepository.get_instance()
    repo.add_fish_to_inventory("seller", _fish("f-1"))
    repo.add_tokens("buyer", 10)

    listing = repo.create_market_listing("seller", "f-1", 40)
    response = client.post(
        f"/market/buy/{listing['listing_id']}",
        json={"buyer_id": "buyer"},
    )
    assert response.status_code == 400
    # nothing moved on the buy side: tokens stay put, fish stays in the listing
    assert repo.get_fish("buyer", "f-1") is None
    assert repo.get_tokens("buyer") == 10
    assert repo.get_tokens("seller") == 0
    # listing remains active so it can still be bought by someone funded
    active_listings = repo.list_market_listings()
    assert any(l["listing_id"] == listing["listing_id"] for l in active_listings)


# ---------- Inventory / aquarium consistency on list and buy ----------


def test_listing_removes_fish_from_inventory_and_aquarium(client):
    repo = MockRepository.get_instance()
    repo.add_fish_to_inventory("kit-1", _fish("f-1", species_id="bluefin_tuna"))

    # before listing: fish is in inventory and aquarium
    inv_before = client.get("/fishing/inventory/kit-1").json()
    assert any(f["fish_id"] == "f-1" for f in inv_before["fish"])
    aq_before = client.get("/aquarium/kit-1").json()
    assert aq_before["collected_species"] == 1

    client.post(
        "/market/list",
        json={"user_id": "kit-1", "fish_id": "f-1", "price": 50},
    )

    # after listing: gone from both
    inv_after = client.get("/fishing/inventory/kit-1").json()
    assert all(f["fish_id"] != "f-1" for f in inv_after["fish"])
    aq_after = client.get("/aquarium/kit-1").json()
    assert aq_after["collected_species"] == 0


def test_buy_delivers_fish_to_buyer_inventory_and_aquarium(client):
    repo = MockRepository.get_instance()
    repo.add_fish_to_inventory("seller", _fish("f-1", species_id="bluefin_tuna"))
    repo.add_tokens("buyer", 100)
    listing = repo.create_market_listing("seller", "f-1", 40)

    response = client.post(
        f"/market/buy/{listing['listing_id']}",
        json={"buyer_id": "buyer"},
    )
    assert response.status_code == 200

    # Buyer now owns the fish
    buyer_inv = client.get("/fishing/inventory/buyer").json()
    assert any(f["fish_id"] == "f-1" for f in buyer_inv["fish"])
    # Buyer's aquarium reflects the new species
    buyer_aq = client.get("/aquarium/buyer").json()
    assert buyer_aq["collected_species"] == 1
    assert buyer_aq["fish"][0]["species_id"] == "bluefin_tuna"
    # Seller no longer owns it (the listing already removed it)
    seller_inv = client.get("/fishing/inventory/seller").json()
    assert all(f["fish_id"] != "f-1" for f in seller_inv["fish"])


def test_unlist_returns_fish_to_seller(client):
    repo = MockRepository.get_instance()
    repo.add_fish_to_inventory("seller", _fish("f-1"))
    listing = repo.create_market_listing("seller", "f-1", 40)
    # gone from seller inventory while listed
    assert repo.get_fish("seller", "f-1") is None

    response = client.delete(
        f"/market/listings/{listing['listing_id']}?seller_id=seller"
    )
    assert response.status_code == 200
    # fish back in seller's inventory after unlist
    assert repo.get_fish("seller", "f-1") is not None


def test_buy_sets_suggested_price_to_paid_price(client):
    repo = MockRepository.get_instance()
    # Fish was caught with a low suggested price (50)
    repo.add_fish_to_inventory("seller", _fish("f-1", sell_value=50))
    repo.add_tokens("buyer", 200)
    # Seller listed it for 90 — that's what the buyer paid
    listing = repo.create_market_listing("seller", "f-1", 90)

    response = client.post(
        f"/market/buy/{listing['listing_id']}",
        json={"buyer_id": "buyer"},
    )
    assert response.status_code == 200

    bought = repo.get_fish("buyer", "f-1")
    assert bought is not None
    assert bought["suggested_price"] == 90, (
        "buyer's relist default should be the price they paid, not the original catch-time value"
    )


def test_cannot_list_same_fish_twice(client):
    repo = MockRepository.get_instance()
    repo.add_fish_to_inventory("kit-1", _fish("f-1"))

    first = client.post(
        "/market/list",
        json={"user_id": "kit-1", "fish_id": "f-1", "price": 50},
    )
    assert first.status_code == 200

    second = client.post(
        "/market/list",
        json={"user_id": "kit-1", "fish_id": "f-1", "price": 50},
    )
    assert second.status_code == 400


# ---------- Token leaderboard ----------


def test_token_leaderboard_excludes_cats(client):
    repo = MockRepository.get_instance()
    repo.add_tokens("kit-1", 50)
    repo.add_tokens("kit-2", 30)
    repo.set_user_role("cat-1", "cat")
    repo.add_tokens("cat-1", 9999)  # bypassing the service to simulate dirty data

    response = client.get("/leaderboard/tokens")
    assert response.status_code == 200
    rows = response.json()
    user_ids = [r["user_id"] for r in rows]

    assert "cat-1" not in user_ids
    assert user_ids[0] == "kit-1"
    assert rows[0]["tokens"] == 50
