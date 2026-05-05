"""MongoDB-backed repository for CatCh game state."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pymongo import MongoClient, ReturnDocument

from app.config import settings

SERVICE_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR_CANDIDATES = [
    Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else None,
    SERVICE_ROOT / "data",
    REPO_ROOT / "data",
]
DATA_DIRS = [path for path in DATA_DIR_CANDIDATES if path is not None]
PROBLEM_DATASET_PATHS = [
    (
        Path(os.environ["PROBLEM_DATASET_PATH"])
        if os.environ.get("PROBLEM_DATASET_PATH")
        else None
    ),
    *(data_dir / "judgeable_problems.json" for data_dir in DATA_DIRS),
]
FISH_SPECIES_PATHS = [
    (
        Path(os.environ["FISH_SPECIES_PATH"])
        if os.environ.get("FISH_SPECIES_PATH")
        else None
    ),
    *(data_dir / "fish_species.json" for data_dir in DATA_DIRS),
]


def _load_json_from_first_existing(paths: list[Optional[Path]]) -> list[dict]:
    """Load JSON records from the first existing path."""

    dataset_path = next((path for path in paths if path and path.exists()), None)
    if dataset_path is None:
        return []
    with open(dataset_path, "r", encoding="utf-8") as file:
        return json.load(file)


class MongoRepository:
    """MongoDB implementation of the game repository protocol."""

    _instance: Optional["MongoRepository"] = None

    def __init__(self) -> None:
        self.client = MongoClient(settings.mongo_url, serverSelectionTimeoutMS=5000)
        self.db = self.client[settings.mongo_db]
        self._ensure_indexes()
        self._seed_static_data()

    @classmethod
    def get_instance(cls) -> "MongoRepository":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_indexes(self) -> None:
        self.db.users.create_index("email")
        self.db.users.create_index("username")
        self.db.ponds.create_index("visibility")
        self.db.ponds.create_index("room_code")
        self.db.problems.create_index("pond_id")
        self.db.inventory.create_index([("user_id", 1), ("fish_id", 1)], unique=True)
        self.db.tokens.create_index("user_id", unique=True)
        self.db.attempts.create_index([("user_id", 1), ("problem_id", 1)], unique=True)
        self.db.submissions.create_index([("user_id", 1), ("problem_id", 1)])
        self.db.market_listings.create_index("status")
        self.db.uncaught.create_index([("user_id", 1), ("problem_id", 1)], unique=True)

    def _seed_static_data(self) -> None:
        problem_records = _load_json_from_first_existing(PROBLEM_DATASET_PATHS)
        if problem_records:
            problem_ids = [entry["id"] for entry in problem_records]
            self.db.problems.delete_many(
                {
                    "_id": {"$nin": problem_ids},
                    "pond_id": {"$exists": False},
                    "source": {"$ne": "teacher"},
                }
            )
            for entry in problem_records:
                self.db.problems.replace_one(
                    {"_id": entry["id"]},
                    {"_id": entry["id"], **entry},
                    upsert=True,
                )
        if self.db.fish_species.estimated_document_count() == 0:
            for entry in _load_json_from_first_existing(FISH_SPECIES_PATHS):
                self.db.fish_species.replace_one(
                    {"_id": entry["id"]},
                    {"_id": entry["id"], **entry},
                    upsert=True,
                )

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        profile = self.db.users.find_one({"_id": user_id}, {"_id": False})
        if profile:
            profile.setdefault("role", "kitten")
            return profile
        return {"user_id": user_id, "username": user_id, "role": "kitten"}

    def get_user_role(self, user_id: str) -> str:
        profile = self.db.users.find_one({"_id": user_id}, {"role": 1})
        if profile and profile.get("role") in ("kitten", "cat"):
            return profile["role"]
        return "kitten"

    def set_user_role(self, user_id: str, role: str) -> None:
        if role not in ("kitten", "cat"):
            raise ValueError(f"unknown role: {role}")
        self.db.users.update_one(
            {"_id": user_id},
            {"$set": {"role": role, "user_id": user_id}},
            upsert=True,
        )

    def list_user_ids_by_role(self, role: str) -> List[str]:
        if role not in ("kitten", "cat"):
            return []
        return [doc["_id"] for doc in self.db.users.find({"role": role}, {"_id": 1})]

    def get_user_flag(self, user_id: str, flag: str) -> bool:
        profile = self.db.users.find_one({"_id": user_id}, {flag: 1})
        return bool(profile and profile.get(flag, False))

    def set_user_flag(self, user_id: str, flag: str, value: bool) -> None:
        self.db.users.update_one(
            {"_id": user_id},
            {"$set": {flag: value, "user_id": user_id}},
            upsert=True,
        )

    def list_problems(self) -> List[Dict[str, Any]]:
        return list(
            self.db.problems.find(
                {"visibility": {"$ne": "private"}},
                {"_id": False},
            )
        )

    def get_problem(self, problem_id: str) -> Optional[Dict[str, Any]]:
        return self.db.problems.find_one({"_id": problem_id}, {"_id": False})

    def create_pond(self, pond: Dict[str, Any]) -> Dict[str, Any]:
        stored = {**pond, "problem_ids": pond.get("problem_ids", [])}
        self.db.ponds.replace_one(
            {"_id": stored["pond_id"]},
            {"_id": stored["pond_id"], **stored},
            upsert=True,
        )
        return stored

    def get_pond(self, pond_id: str) -> Optional[Dict[str, Any]]:
        return self.db.ponds.find_one({"_id": pond_id}, {"_id": False})

    def list_public_ponds(self) -> List[Dict[str, Any]]:
        return list(self.db.ponds.find({"visibility": "public"}, {"_id": False}))

    def list_private_ponds(self, user_id: str) -> List[Dict[str, Any]]:
        return list(
            self.db.ponds.find(
                {
                    "visibility": "private",
                    "member_user_ids": user_id,
                },
                {"_id": False},
            )
        )

    def join_private_pond(self, user_id: str, room_code: str) -> Dict[str, Any]:
        normalized_code = room_code.strip().upper()
        pond = self.db.ponds.find_one_and_update(
            {"visibility": "private", "room_code": normalized_code},
            {"$addToSet": {"member_user_ids": user_id}},
            return_document=ReturnDocument.AFTER,
            projection={"_id": False},
        )
        if pond is None:
            raise ValueError("private pond not found")
        return dict(pond)

    def list_teacher_ponds(self, cat_id: str) -> List[Dict[str, Any]]:
        return list(self.db.ponds.find({"cat_id": cat_id}, {"_id": False}))

    def add_problem_to_pond(
        self, pond_id: str, problem: Dict[str, Any]
    ) -> Dict[str, Any]:
        if self.get_pond(pond_id) is None:
            raise ValueError("pond not found")
        self.db.problems.replace_one(
            {"_id": problem["id"]},
            {"_id": problem["id"], **problem},
            upsert=True,
        )
        self.db.ponds.update_one(
            {"_id": pond_id},
            {"$addToSet": {"problem_ids": problem["id"]}},
        )
        return problem

    def update_pond_problem(
        self, pond_id: str, problem_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        pond = self.get_pond(pond_id) or {}
        if problem_id not in pond.get("problem_ids", []):
            raise ValueError("pond problem not found")
        updated = self.db.problems.find_one_and_update(
            {"_id": problem_id, "pond_id": pond_id},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
            projection={"_id": False},
        )
        if updated is None:
            raise ValueError("problem not found")
        return dict(updated)

    def delete_pond_problem(self, pond_id: str, problem_id: str) -> None:
        pond = self.get_pond(pond_id) or {}
        if problem_id not in pond.get("problem_ids", []):
            raise ValueError("pond problem not found")
        self.db.problems.delete_one({"_id": problem_id, "pond_id": pond_id})
        self.db.ponds.update_one(
            {"_id": pond_id},
            {"$pull": {"problem_ids": problem_id}},
        )

    def list_pond_problems(self, pond_id: str) -> List[Dict[str, Any]]:
        pond = self.get_pond(pond_id) or {}
        problem_ids = pond.get("problem_ids", [])
        if not problem_ids:
            return []
        return list(
            self.db.problems.find(
                {"_id": {"$in": problem_ids}},
                {"_id": False},
            )
        )

    def get_fishing_chances(self, user_id: str) -> int:
        doc = self.db.tokens.find_one({"user_id": user_id})
        return int(doc.get("fishing_chances", 0)) if doc else 0

    def add_fishing_chances(self, user_id: str, n: int) -> int:
        updated = self.db.tokens.find_one_and_update(
            {"user_id": user_id},
            {"$inc": {"fishing_chances": n}, "$setOnInsert": {"tokens": 0}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return int(updated.get("fishing_chances", 0))

    def consume_fishing_chance(self, user_id: str) -> int:
        updated = self.db.tokens.find_one_and_update(
            {"user_id": user_id, "fishing_chances": {"$gt": 0}},
            {"$inc": {"fishing_chances": -1}},
            return_document=ReturnDocument.AFTER,
        )
        if updated is None:
            raise ValueError(f"user {user_id} has no fishing chances")
        return int(updated.get("fishing_chances", 0))

    def list_fish_species(self) -> List[Dict[str, Any]]:
        return list(self.db.fish_species.find({}, {"_id": False}))

    def get_fish_species(self, species_id: str) -> Optional[Dict[str, Any]]:
        return self.db.fish_species.find_one({"id": species_id}, {"_id": False})

    def add_fish_to_inventory(self, user_id: str, fish: Dict[str, Any]) -> None:
        # Strip user_id from the incoming fish dict — fish returned from
        # remove_fish_from_inventory carries the previous owner's user_id,
        # and `{"user_id": user_id, **fish}` would let the spread clobber it,
        # silently re-inserting the doc under the previous owner.
        body = {k: v for k, v in fish.items() if k != "user_id"}
        self.db.inventory.replace_one(
            {"user_id": user_id, "fish_id": fish["fish_id"]},
            {"user_id": user_id, **body},
            upsert=True,
        )

    def get_inventory(self, user_id: str) -> List[Dict[str, Any]]:
        return list(self.db.inventory.find({"user_id": user_id}, {"_id": False}))

    def list_inventory_user_ids(self) -> List[str]:
        return self.db.inventory.distinct("user_id")

    def get_fish(self, user_id: str, fish_id: str) -> Optional[Dict[str, Any]]:
        return self.db.inventory.find_one(
            {"user_id": user_id, "fish_id": fish_id},
            {"_id": False},
        )

    def remove_fish_from_inventory(
        self, user_id: str, fish_id: str
    ) -> Optional[Dict[str, Any]]:
        removed = self.db.inventory.find_one_and_delete(
            {"user_id": user_id, "fish_id": fish_id},
            projection={"_id": False},
        )
        return removed

    def get_tokens(self, user_id: str) -> int:
        doc = self.db.tokens.find_one({"user_id": user_id})
        return int(doc.get("tokens", 0)) if doc else 0

    def add_tokens(self, user_id: str, n: int) -> int:
        updated = self.db.tokens.find_one_and_update(
            {"user_id": user_id},
            {"$inc": {"tokens": n}, "$setOnInsert": {"fishing_chances": 0}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return int(updated.get("tokens", 0))

    def list_token_balances(self) -> List[Dict[str, Any]]:
        balances = {
            doc["user_id"]: doc for doc in self.db.tokens.find({}, {"_id": False})
        }
        for user in self.db.users.find({"role": "kitten"}, {"_id": False}):
            balances.setdefault(
                user["user_id"],
                {
                    "user_id": user["user_id"],
                    "tokens": 0,
                    "fishing_chances": 0,
                },
            )
        return list(balances.values())

    def record_submission(
        self,
        user_id: str,
        problem_id: str,
        passed: bool,
        code: str,
    ) -> str:
        sub_id = str(uuid.uuid4())
        self.db.submissions.insert_one(
            {
                "_id": sub_id,
                "id": sub_id,
                "user_id": user_id,
                "problem_id": problem_id,
                "passed": passed,
                "code": code,
            }
        )
        return sub_id

    def list_submissions(self, user_id: str) -> List[Dict[str, Any]]:
        return list(self.db.submissions.find({"user_id": user_id}, {"_id": False}))

    def get_attempt_state(self, user_id: str, problem_id: str) -> Dict[str, Any]:
        state = (
            self.db.attempts.find_one(
                {"user_id": user_id, "problem_id": problem_id},
                {"_id": False},
            )
            or {}
        )
        return {
            "attempts_used": int(state.get("attempts_used", 0)),
            "completed": bool(state.get("completed", False)),
            "exhausted": bool(state.get("exhausted", False)),
        }

    def list_problem_attempts(self, user_id: str) -> List[Dict[str, Any]]:
        return list(self.db.attempts.find({"user_id": user_id}, {"_id": False}))

    def reset_problem_attempts(self, user_id: str, problem_ids: List[str]) -> None:
        self.db.attempts.delete_many(
            {"user_id": user_id, "problem_id": {"$in": problem_ids}}
        )

    def record_problem_attempt(
        self,
        user_id: str,
        problem_id: str,
        passed: bool,
        code: str,
        max_attempts: int,
    ) -> Dict[str, Any]:
        current = self.get_attempt_state(user_id, problem_id)
        if current["completed"] or current["exhausted"]:
            return current
        attempts_used = current["attempts_used"] + 1
        exhausted = not passed and attempts_used >= max_attempts
        updated = self.db.attempts.find_one_and_update(
            {"user_id": user_id, "problem_id": problem_id},
            {
                "$set": {
                    "user_id": user_id,
                    "problem_id": problem_id,
                    "attempts_used": attempts_used,
                    "completed": passed,
                    "exhausted": exhausted,
                    "last_code": code,
                }
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
            projection={"_id": False},
        )
        return dict(updated)

    def add_uncaught_problem(
        self,
        user_id: str,
        problem: Dict[str, Any],
        attempts_used: int,
    ) -> bool:
        result = self.db.uncaught.update_one(
            {"user_id": user_id, "problem_id": problem["id"]},
            {
                "$setOnInsert": {
                    "user_id": user_id,
                    "problem_id": problem["id"],
                    "title": problem["title"],
                    "instructions": problem.get("instructions", ""),
                    "solution_code": problem.get("solution_code", ""),
                    "solution_explanation": problem.get("solution_explanation"),
                    "attempts_used": attempts_used,
                }
            },
            upsert=True,
        )
        return bool(result.upserted_id)

    def list_uncaught_problems(self, user_id: str) -> List[Dict[str, Any]]:
        return list(self.db.uncaught.find({"user_id": user_id}, {"_id": False}))

    def create_market_listing(
        self,
        user_id: str,
        fish_id: str,
        price: int,
    ) -> Dict[str, Any]:
        fish = self.get_fish(user_id, fish_id)
        if fish is None:
            raise ValueError("fish not found")
        if fish.get("rarity") == "common":
            raise ValueError(
                "only uncommon or rarer fish can be listed on the marketplace"
            )

        # Move the fish out of the seller's inventory and into the listing.
        # Keeps the aquarium and "your eligible fish" view in sync, and
        # prevents double-listing.
        removed = self.remove_fish_from_inventory(user_id, fish_id)
        if removed is None:
            raise ValueError("fish not found")
        # Drop user_id from the inventory doc before nesting it inside the listing.
        listing_fish = {k: v for k, v in removed.items() if k != "user_id"}

        listing = {
            "listing_id": str(uuid.uuid4()),
            "seller_id": user_id,
            "fish": listing_fish,
            "price": int(price),
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.db.market_listings.insert_one({"_id": listing["listing_id"], **listing})
        return listing

    def list_market_listings(
        self,
        rarity: Optional[str] = None,
        species_id: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        sort_by: str = "newest",
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"status": "active"}
        if rarity is not None:
            query["fish.rarity"] = rarity
        if species_id is not None:
            query["fish.species_id"] = species_id
        if min_price is not None or max_price is not None:
            price_query: Dict[str, Any] = {}
            if min_price is not None:
                price_query["$gte"] = min_price
            if max_price is not None:
                price_query["$lte"] = max_price
            query["price"] = price_query

        cursor = self.db.market_listings.find(query, {"_id": False})
        results = list(cursor)
        if sort_by == "price_asc":
            results.sort(key=lambda r: int(r["price"]))
        elif sort_by == "price_desc":
            results.sort(key=lambda r: int(r["price"]), reverse=True)
        elif sort_by == "rarity":
            order = {
                "common": 0,
                "uncommon": 1,
                "rare": 2,
                "epic": 3,
                "legendary": 4,
            }
            results.sort(
                key=lambda r: order.get(r["fish"].get("rarity"), 99), reverse=True
            )
        else:
            results.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return results

    def unlist_market_listing(
        self,
        listing_id: str,
        seller_id: str,
    ) -> Dict[str, Any]:
        updated = self.db.market_listings.find_one_and_update(
            {"listing_id": listing_id, "status": "active", "seller_id": seller_id},
            {"$set": {"status": "cancelled"}},
            return_document=ReturnDocument.AFTER,
            projection={"_id": False},
        )
        if updated is None:
            existing = self.db.market_listings.find_one(
                {"listing_id": listing_id}, {"_id": False}
            )
            if existing is None or existing.get("status") != "active":
                raise ValueError("listing not found")
            raise ValueError("only the seller may unlist this fish")
        # Return the fish to the seller — they had it before listing.
        self.add_fish_to_inventory(seller_id, updated["fish"])
        return updated

    def buy_market_listing(
        self,
        listing_id: str,
        buyer_id: str,
    ) -> Dict[str, Any]:
        # Atomically claim the listing first — only one buyer wins. If we don't
        # win, no inventory or token state is touched.
        claimed = self.db.market_listings.find_one_and_update(
            {"listing_id": listing_id, "status": "active"},
            {"$set": {"status": "pending", "buyer_id": buyer_id}},
            return_document=ReturnDocument.AFTER,
            projection={"_id": False},
        )
        if claimed is None:
            raise ValueError("listing not found")

        seller_id = claimed["seller_id"]
        price = int(claimed["price"])

        try:
            if seller_id == buyer_id:
                raise ValueError("buyer cannot purchase their own listing")
            if self.get_user_role(buyer_id) != "kitten":
                raise ValueError("only kittens can buy from the marketplace")
            if self.get_tokens(buyer_id) < price:
                raise ValueError("buyer has insufficient tokens")
        except ValueError:
            # Roll back the claim so the listing is buyable again.
            self.db.market_listings.update_one(
                {"listing_id": listing_id},
                {"$set": {"status": "active"}, "$unset": {"buyer_id": ""}},
            )
            raise

        # The fish already left the seller's inventory at list time, so we just
        # transfer tokens and deliver from the listing. Bump suggested_price to
        # the price the buyer actually paid so a future relist defaults above
        # the buy-in instead of the original catch-time suggestion.
        delivered = {**claimed["fish"], "suggested_price": price}
        self.add_tokens(buyer_id, -price)
        self.add_tokens(seller_id, price)
        self.add_fish_to_inventory(buyer_id, delivered)
        self.db.market_listings.update_one(
            {"listing_id": listing_id},
            {"$set": {"status": "sold"}},
        )
        claimed["status"] = "sold"
        return claimed
