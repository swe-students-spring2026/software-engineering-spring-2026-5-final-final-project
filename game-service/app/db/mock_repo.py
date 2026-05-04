"""In-memory repository, phase 1 only.

Loads problems from app/seeds/problems.json and fish species from
data/fish_species.json on first instantiation. fishing_chances, inventory,
tokens, and submissions live in dicts/lists; they reset whenever the
process restarts. That's intentional for phase 1.
"""

import json
import os
import uuid
from pathlib import Path
from threading import RLock
from typing import List, Optional, Dict, Any

SEEDS_PATH = Path(__file__).parent.parent / "seeds" / "problems.json"
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
    SEEDS_PATH,
]
FISH_SPECIES_PATHS = [
    (
        Path(os.environ["FISH_SPECIES_PATH"])
        if os.environ.get("FISH_SPECIES_PATH")
        else None
    ),
    *(data_dir / "fish_species.json" for data_dir in DATA_DIRS),
]


class MockRepository:
    _instance: Optional["MockRepository"] = None
    _instance_lock = RLock()

    def __init__(self) -> None:
        self._problems: Dict[str, Dict[str, Any]] = {}
        self._ponds: Dict[str, Dict[str, Any]] = {}
        self._fishing: Dict[str, int] = {}
        self._submissions: List[Dict[str, Any]] = []
        self._fish_species: Dict[str, Dict[str, Any]] = {}
        self._inventory: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._tokens: Dict[str, int] = {}
        self._attempts: Dict[tuple[str, str], Dict[str, Any]] = {}
        self._uncaught: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._market_listings: Dict[str, Dict[str, Any]] = {}
        self._mutate_lock = RLock()
        self._load_seeds()
        self._load_fish_species()

    @classmethod
    def get_instance(cls) -> "MockRepository":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """For tests. Wipes the singleton so the next get_instance reloads seeds."""
        with cls._instance_lock:
            cls._instance = None

    def _load_seeds(self) -> None:
        dataset_path = next(
            (p for p in PROBLEM_DATASET_PATHS if p is not None and p.exists()),
            None,
        )
        if dataset_path is None:
            return
        with open(dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for entry in data:
            self._problems[entry["id"]] = entry

    def _load_fish_species(self) -> None:
        species_path = next(
            (p for p in FISH_SPECIES_PATHS if p is not None and p.exists()),
            None,
        )
        if species_path is None:
            return
        with open(species_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for entry in data:
            self._fish_species[entry["id"]] = entry

    # --- problems ---

    def list_problems(self) -> List[Dict[str, Any]]:
        return [
            problem
            for problem in self._problems.values()
            if problem.get("visibility") != "private"
        ]

    def get_problem(self, problem_id: str) -> Optional[Dict[str, Any]]:
        return self._problems.get(problem_id)

    def create_pond(self, pond: Dict[str, Any]) -> Dict[str, Any]:
        with self._mutate_lock:
            self._ponds[pond["pond_id"]] = {**pond, "problem_ids": []}
            return self._ponds[pond["pond_id"]]

    def get_pond(self, pond_id: str) -> Optional[Dict[str, Any]]:
        return self._ponds.get(pond_id)

    def list_public_ponds(self) -> List[Dict[str, Any]]:
        return [
            pond for pond in self._ponds.values() if pond.get("visibility") == "public"
        ]

    def list_private_ponds(self, user_id: str) -> List[Dict[str, Any]]:
        return [
            pond
            for pond in self._ponds.values()
            if pond.get("visibility") == "private"
            and user_id in pond.get("member_user_ids", [user_id])
        ]

    def add_problem_to_pond(
        self, pond_id: str, problem: Dict[str, Any]
    ) -> Dict[str, Any]:
        with self._mutate_lock:
            pond = self._ponds.get(pond_id)
            if pond is None:
                raise ValueError("pond not found")
            self._problems[problem["id"]] = problem
            pond.setdefault("problem_ids", []).append(problem["id"])
            return problem

    def list_pond_problems(self, pond_id: str) -> List[Dict[str, Any]]:
        pond = self._ponds.get(pond_id, {})
        return [
            self._problems[problem_id]
            for problem_id in pond.get("problem_ids", [])
            if problem_id in self._problems
        ]

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        return {"user_id": user_id, "username": user_id}

    # --- fishing chances ---

    def get_fishing_chances(self, user_id: str) -> int:
        return self._fishing.get(user_id, 0)

    def add_fishing_chances(self, user_id: str, n: int) -> int:
        with self._mutate_lock:
            updated = self._fishing.get(user_id, 0) + n
            self._fishing[user_id] = updated
            return updated

    def consume_fishing_chance(self, user_id: str) -> int:
        with self._mutate_lock:
            current = self._fishing.get(user_id, 0)
            if current <= 0:
                raise ValueError(f"user {user_id} has no fishing chances")
            self._fishing[user_id] = current - 1
            return current - 1

    # --- fish species ---

    def list_fish_species(self) -> List[Dict[str, Any]]:
        return list(self._fish_species.values())

    def get_fish_species(self, species_id: str) -> Optional[Dict[str, Any]]:
        return self._fish_species.get(species_id)

    # --- inventory ---

    def add_fish_to_inventory(self, user_id: str, fish: Dict[str, Any]) -> None:
        with self._mutate_lock:
            self._inventory.setdefault(user_id, {})[fish["fish_id"]] = fish

    def get_inventory(self, user_id: str) -> List[Dict[str, Any]]:
        return list(self._inventory.get(user_id, {}).values())

    def list_inventory_user_ids(self) -> List[str]:
        return list(self._inventory.keys())

    def get_fish(self, user_id: str, fish_id: str) -> Optional[Dict[str, Any]]:
        return self._inventory.get(user_id, {}).get(fish_id)

    def remove_fish_from_inventory(
        self, user_id: str, fish_id: str
    ) -> Optional[Dict[str, Any]]:
        with self._mutate_lock:
            return self._inventory.get(user_id, {}).pop(fish_id, None)

    # --- tokens ---

    def get_tokens(self, user_id: str) -> int:
        return self._tokens.get(user_id, 0)

    def add_tokens(self, user_id: str, n: int) -> int:
        with self._mutate_lock:
            updated = self._tokens.get(user_id, 0) + n
            self._tokens[user_id] = updated
            return updated

    def list_token_balances(self) -> List[Dict[str, Any]]:
        return [
            {"user_id": user_id, "tokens": tokens}
            for user_id, tokens in self._tokens.items()
        ]

    # --- submissions ---

    def record_submission(
        self,
        user_id: str,
        problem_id: str,
        passed: bool,
        code: str,
    ) -> str:
        sub_id = str(uuid.uuid4())
        with self._mutate_lock:
            self._submissions.append(
                {
                    "id": sub_id,
                    "user_id": user_id,
                    "problem_id": problem_id,
                    "passed": passed,
                    "code": code,
                }
            )
        return sub_id

    def list_submissions(self, user_id: str) -> List[Dict[str, Any]]:
        return [s for s in self._submissions if s["user_id"] == user_id]

    # --- problem attempt state ---

    def get_attempt_state(self, user_id: str, problem_id: str) -> Dict[str, Any]:
        state = self._attempts.get((user_id, problem_id), {})
        return {
            "attempts_used": int(state.get("attempts_used", 0)),
            "completed": bool(state.get("completed", False)),
            "exhausted": bool(state.get("exhausted", False)),
        }

    def record_problem_attempt(
        self,
        user_id: str,
        problem_id: str,
        passed: bool,
        code: str,
        max_attempts: int,
    ) -> Dict[str, Any]:
        with self._mutate_lock:
            key = (user_id, problem_id)
            state = self._attempts.setdefault(
                key,
                {
                    "attempts_used": 0,
                    "completed": False,
                    "exhausted": False,
                    "last_code": None,
                },
            )
            if state["completed"] or state["exhausted"]:
                return dict(state)

            state["attempts_used"] += 1
            state["last_code"] = code
            if passed:
                state["completed"] = True
            elif state["attempts_used"] >= max_attempts:
                state["exhausted"] = True
            return dict(state)

    def list_problem_attempts(self, user_id: str) -> List[Dict[str, Any]]:
        return [
            {"user_id": uid, "problem_id": problem_id, **state}
            for (uid, problem_id), state in self._attempts.items()
            if uid == user_id
        ]

    # --- wrong-answer review ---

    def add_uncaught_problem(
        self,
        user_id: str,
        problem: Dict[str, Any],
        attempts_used: int,
    ) -> bool:
        with self._mutate_lock:
            user_uncaught = self._uncaught.setdefault(user_id, {})
            problem_id = problem["id"]
            if problem_id in user_uncaught:
                return False
            user_uncaught[problem_id] = {
                "user_id": user_id,
                "problem_id": problem_id,
                "title": problem["title"],
                "solution_code": problem.get("solution_code", ""),
                "solution_explanation": problem.get("solution_explanation"),
                "attempts_used": attempts_used,
            }
            return True

    def list_uncaught_problems(self, user_id: str) -> List[Dict[str, Any]]:
        return list(self._uncaught.get(user_id, {}).values())

    # --- marketplace ---

    def create_market_listing(
        self,
        user_id: str,
        fish_id: str,
        price: int,
    ) -> Dict[str, Any]:
        with self._mutate_lock:
            fish = self.get_fish(user_id, fish_id)
            if fish is None:
                raise ValueError("fish not found")
            if not fish.get("marketplace_eligible", False):
                raise ValueError("fish is not marketplace eligible")

            listing = {
                "listing_id": str(uuid.uuid4()),
                "seller_id": user_id,
                "fish": fish,
                "price": price,
                "status": "active",
            }
            self._market_listings[listing["listing_id"]] = listing
            return listing

    def list_market_listings(self) -> List[Dict[str, Any]]:
        return [
            listing
            for listing in self._market_listings.values()
            if listing["status"] == "active"
        ]

    def buy_market_listing(
        self,
        listing_id: str,
        buyer_id: str,
    ) -> Dict[str, Any]:
        with self._mutate_lock:
            listing = self._market_listings.get(listing_id)
            if listing is None or listing["status"] != "active":
                raise ValueError("listing not found")
            seller_id = listing["seller_id"]
            if seller_id == buyer_id:
                raise ValueError("buyer cannot purchase their own listing")

            price = int(listing["price"])
            buyer_tokens = self.get_tokens(buyer_id)
            if buyer_tokens < price:
                raise ValueError("buyer has insufficient tokens")

            fish = self.remove_fish_from_inventory(
                seller_id,
                listing["fish"]["fish_id"],
            )
            if fish is None:
                listing["status"] = "cancelled"
                raise ValueError("listed fish is no longer available")

            self.add_tokens(buyer_id, -price)
            self.add_tokens(seller_id, price)
            self.add_fish_to_inventory(buyer_id, fish)
            listing["status"] = "sold"
            listing["buyer_id"] = buyer_id
            return listing
