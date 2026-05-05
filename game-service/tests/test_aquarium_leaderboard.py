from datetime import datetime, timezone

from app.db.mock_repo import MockRepository


def _fish(
    fish_id: str,
    species_id: str = "bluefin_tuna",
    rarity: str = "rare",
    marketplace_eligible: bool = True,
    is_system_sellable: bool = False,
    price: int = 70,
) -> dict:
    return {
        "fish_id": fish_id,
        "species_id": species_id,
        "species_name": "Bluefin Tuna",
        "species": "Thunnus thynnus",
        "rarity": rarity,
        "quality": "normal",
        "size_cm": 120.0,
        "weight_g": 18000.0,
        "image_url": "/fish_images/bluefin_tuna.png",
        "image_path": "/fish_images/bluefin_tuna.png",
        "description": "A fast open-water fish.",
        "caught_at": datetime.now(timezone.utc).isoformat(),
        "suggested_price": price,
        "sell_value": price,
        "sell_value_tokens": price,
        "marketplace_eligible": marketplace_eligible,
        "is_system_sellable": is_system_sellable,
        "is_small": False,
    }


def test_aquarium_tracks_unique_species(client):
    repo = MockRepository.get_instance()
    repo.add_fish_to_inventory("u1", _fish("fish-1", "bluefin_tuna"))
    repo.add_fish_to_inventory("u1", _fish("fish-2", "bluefin_tuna"))

    response = client.get("/aquarium/u1")

    assert response.status_code == 200
    data = response.json()
    assert data["collected_species"] == 1
    assert data["total_species"] == 50
    assert data["fish"][0]["quantity"] == 2


def test_token_leaderboard_ranks_users_by_tokens(client):
    repo = MockRepository.get_instance()
    repo.add_tokens("u1", 5)
    repo.add_tokens("u2", 10)

    response = client.get("/leaderboard/tokens")

    assert response.status_code == 200
    assert response.json()[0] == {
        "user_id": "u2",
        "username": "u2",
        "tokens": 10,
    }


def test_aquarium_leaderboard_ranks_users_by_collection(client):
    repo = MockRepository.get_instance()
    repo.add_fish_to_inventory("u1", _fish("fish-1", "bluefin_tuna"))
    repo.add_fish_to_inventory("u2", _fish("fish-2", "bluefin_tuna"))
    repo.add_fish_to_inventory("u2", _fish("fish-3", "koi"))

    response = client.get("/leaderboard/aquarium")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["user_id"] == "u2"
    assert data[0]["collected_species"] == 2
