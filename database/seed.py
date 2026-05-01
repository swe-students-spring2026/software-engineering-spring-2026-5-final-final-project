"""Seed script — populates MongoDB with evaluation data.

Usage:
    python database/seed.py
"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "pennywise")


def _month_start(base: datetime, offset: int) -> datetime:
    """Return the first day of the month `offset` months after `base`."""
    total_months = base.year * 12 + (base.month - 1) + offset
    year, month = divmod(total_months, 12)
    return datetime(year, month + 1, 1)


def run():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    # ── clear existing seed data ──────────────────────────────────────────
    for coll in ("users", "transactions", "budgets", "categories"):
        db[coll].delete_many({})

    # ── users ─────────────────────────────────────────────────────────────
    password_hash = bcrypt.hashpw(b"password123", bcrypt.gensalt())
    user_docs = [
        {"username": "alice", "password": password_hash, "email": "alice@example.com", "created_at": _now()},
        {"username": "bob",   "password": password_hash, "email": "bob@example.com",   "created_at": _now()},
    ]
    user_ids = db.users.insert_many(user_docs).inserted_ids
    alice_id, bob_id = user_ids[0], user_ids[1]
    print(f"Inserted {len(user_ids)} users")

    # ── categories ────────────────────────────────────────────────────────
    categories = ["food", "transport", "utilities", "entertainment", "health", "salary", "freelance"]
    db.categories.insert_many([{"name": c} for c in categories])
    print(f"Inserted {len(categories)} categories")

    # ── transactions (3 months of data for both users) ────────────────────
    base = datetime(2026, 2, 1)
    income_schedule = [
        ("salary",   3000.0, 1),
        ("freelance", 500.0, 15),
    ]
    expense_schedule = [
        ("food",          55.0,  3),
        ("food",          40.0, 10),
        ("food",          60.0, 18),
        ("transport",     30.0,  5),
        ("transport",     25.0, 20),
        ("utilities",    120.0,  1),
        ("entertainment", 50.0, 12),
        ("health",        80.0,  7),
    ]

    transactions = []
    for user_id in (alice_id, bob_id):
        for month_offset in range(3):
            month = _month_start(base, month_offset)
            scale = 1 + month_offset * 0.05  # slight monthly variation
            for cat, amt, day in income_schedule:
                transactions.append(_tx("income", amt, cat, month + timedelta(days=day - 1), user_id))
            for cat, amt, day in expense_schedule:
                transactions.append(_tx("expense", round(amt * scale, 2), cat, month + timedelta(days=day - 1), user_id))

    db.transactions.insert_many(transactions)
    print(f"Inserted {len(transactions)} transactions")

    # ── budgets (current month, per user) ─────────────────────────────────
    budget_templates = [
        {"category": "food",          "limit": 200.0},
        {"category": "transport",     "limit": 100.0},
        {"category": "entertainment", "limit":  60.0},
        {"category": "utilities",     "limit": 150.0},
    ]
    budgets = []
    for user_id in (alice_id, bob_id):
        for b in budget_templates:
            budgets.append({**b, "month": "2026-04", "user_id": user_id, "created_at": _now()})

    db.budgets.insert_many(budgets)
    print(f"Inserted {len(budgets)} budgets")

    client.close()
    print("Seed complete.")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tx(tx_type: str, amount: float, category: str, date: datetime, user_id=None) -> dict:
    doc = {
        "type":        tx_type,
        "amount":      amount,
        "category":    category,
        "description": f"Seed {category}",
        "date":        date.strftime("%Y-%m-%d"),
    }
    if user_id is not None:
        doc["user_id"] = user_id
    return doc


if __name__ == "__main__":
    run()
