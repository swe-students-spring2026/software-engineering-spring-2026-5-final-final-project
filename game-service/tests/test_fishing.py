from collections import Counter
from pathlib import Path

from app.db.mock_repo import MockRepository

REPO_ROOT = Path(__file__).resolve().parents[2]
RARITIES = {"common", "uncommon", "rare", "epic", "legendary"}


# --- /fishing/species ---


def test_list_species(client):
    resp = client.get("/fishing/species")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 50
    rarities = {s["rarity"] for s in data}
    assert rarities.issubset(RARITIES)
    assert "epic" in rarities
    assert abs(sum(s["catch_probability"] for s in data) - 100.0) < 0.01

    for s in data:
        assert s["id"] == s["species_id"]
        assert s["name"]
        assert s["species"]
        assert s["description"]
        assert s["catch_probability"] > 0
        assert s["sell_value"] > 0
        assert s["sell_value_tokens"] == s["sell_value"]
        assert s["base_price"] > 0
        assert s["typical_size_cm"] > 0
        assert s["image_url"].startswith("/fish_images/")
        assert s["image_path"] == s["image_url"]
        assert s["image_url"].endswith(".png")
        assert (REPO_ROOT / "data" / s["image_url"].lstrip("/")).exists()
        assert isinstance(s["marketplace_eligible"], bool)
        assert isinstance(s["image_pool"], list)

    image_resp = client.get(data[0]["image_url"])
    assert image_resp.status_code == 200
    assert image_resp.headers["content-type"] == "image/png"


# --- POST /fishing/cast ---


def test_cast_without_chances_returns_400(client):
    resp = client.post("/fishing/cast", params={"user_id": "u1"})
    assert resp.status_code == 400


def test_cast_consumes_chance_and_adds_fish(client):
    repo = MockRepository.get_instance()
    repo.add_fishing_chances("u1", 3)

    resp = client.post("/fishing/cast", params={"user_id": "u1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["remaining_chances"] == 2

    fish = data["fish"]
    assert fish["fish_id"]
    assert fish["species_id"]
    assert fish["species"]
    assert fish["description"]
    assert fish["rarity"] in RARITIES
    assert fish["quality"] in {"normal", "shiny", "perfect"}
    assert fish["size_cm"] > 0
    assert fish["weight_g"] > 0
    assert fish["suggested_price"] >= 1
    assert fish["sell_value"] >= 1
    assert fish["sell_value_tokens"] == fish["sell_value"]
    assert fish["image_path"] == fish["image_url"]
    assert fish["image_url"].endswith(".png")
    assert isinstance(fish["marketplace_eligible"], bool)
    assert isinstance(fish["is_small"], bool)

    inv = repo.get_inventory("u1")
    assert len(inv) == 1
    assert inv[0]["fish_id"] == fish["fish_id"]


def test_cast_decrements_to_zero_then_blocks(client):
    repo = MockRepository.get_instance()
    repo.add_fishing_chances("u1", 1)

    r1 = client.post("/fishing/cast", params={"user_id": "u1"})
    assert r1.status_code == 200
    assert r1.json()["remaining_chances"] == 0

    r2 = client.post("/fishing/cast", params={"user_id": "u1"})
    assert r2.status_code == 400


def test_rarity_distribution_skews_to_common(client):
    """Common should appear far more than legendary across many casts."""
    repo = MockRepository.get_instance()
    repo.add_fishing_chances("u1", 400)

    counts: Counter = Counter()
    for _ in range(400):
        resp = client.post("/fishing/cast", params={"user_id": "u1"})
        assert resp.status_code == 200
        counts[resp.json()["fish"]["rarity"]] += 1

    # Dataset probabilities use 60/25/10/4/1 rarity buckets.
    assert counts["common"] > counts.get("legendary", 0)
    assert counts["common"] > counts.get("rare", 0)


def test_cast_503_when_no_species(client, monkeypatch):
    repo = MockRepository.get_instance()
    repo.add_fishing_chances("u1", 1)
    monkeypatch.setattr(repo, "list_fish_species", lambda: [])

    resp = client.post("/fishing/cast", params={"user_id": "u1"})
    assert resp.status_code == 503
    # chance should NOT be consumed when the dataset is unusable
    assert repo.get_fishing_chances("u1") == 1


# --- GET /fishing/inventory/{user_id} ---


def test_inventory_empty_for_new_user(client):
    resp = client.get("/fishing/inventory/nobody")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "nobody"
    assert data["fish"] == []
    assert data["total_count"] == 0
    assert data["tokens"] == 0
    assert data["fishing_chances"] == 0


def test_inventory_reflects_casts(client):
    repo = MockRepository.get_instance()
    repo.add_fishing_chances("u1", 3)
    for _ in range(3):
        client.post("/fishing/cast", params={"user_id": "u1"})

    resp = client.get("/fishing/inventory/u1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 3
    assert len(data["fish"]) == 3
    assert data["fishing_chances"] == 0


# --- POST /fishing/sell-small/{fish_id} ---


def _cast_a_fish(client, user_id: str = "u1") -> dict:
    repo = MockRepository.get_instance()
    repo.add_fishing_chances(user_id, 1)
    return client.post("/fishing/cast", params={"user_id": user_id}).json()["fish"]


def test_sell_small_404_for_unknown_fish(client):
    resp = client.post(
        "/fishing/sell-small/does-not-exist",
        params={"user_id": "u1"},
    )
    assert resp.status_code == 404


def test_sell_small_refunds_tokens_and_removes_fish(client):
    repo = MockRepository.get_instance()
    # Force a small fish: cast then mutate the stored record.
    fish = _cast_a_fish(client, "u1")
    stored = repo.get_fish("u1", fish["fish_id"])
    stored["is_small"] = True
    stored["marketplace_eligible"] = False
    stored["suggested_price"] = 10  # so refund is predictable

    resp = client.post(
        f"/fishing/sell-small/{fish['fish_id']}",
        params={"user_id": "u1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tokens_earned"] == 5  # 10 * 0.5
    assert data["new_token_balance"] == 5
    assert repo.get_fish("u1", fish["fish_id"]) is None


def test_sell_small_rejects_non_small_fish(client):
    repo = MockRepository.get_instance()
    fish = _cast_a_fish(client, "u1")
    stored = repo.get_fish("u1", fish["fish_id"])
    stored["is_small"] = False

    resp = client.post(
        f"/fishing/sell-small/{fish['fish_id']}",
        params={"user_id": "u1"},
    )
    assert resp.status_code == 400
    # fish should still be in inventory
    assert repo.get_fish("u1", fish["fish_id"]) is not None


def test_sell_small_rejects_marketplace_eligible_fish(client):
    repo = MockRepository.get_instance()
    fish = _cast_a_fish(client, "u1")
    stored = repo.get_fish("u1", fish["fish_id"])
    stored["is_small"] = True
    stored["marketplace_eligible"] = True

    resp = client.post(
        f"/fishing/sell-small/{fish['fish_id']}",
        params={"user_id": "u1"},
    )
    assert resp.status_code == 400
    assert repo.get_fish("u1", fish["fish_id"]) is not None


def test_sell_small_minimum_refund_is_one(client):
    repo = MockRepository.get_instance()
    fish = _cast_a_fish(client, "u1")
    stored = repo.get_fish("u1", fish["fish_id"])
    stored["is_small"] = True
    stored["marketplace_eligible"] = False
    stored["suggested_price"] = 1  # 1 * 0.5 = 0.5 -> rounds up to 1

    resp = client.post(
        f"/fishing/sell-small/{fish['fish_id']}",
        params={"user_id": "u1"},
    )
    assert resp.status_code == 200
    assert resp.json()["tokens_earned"] >= 1
