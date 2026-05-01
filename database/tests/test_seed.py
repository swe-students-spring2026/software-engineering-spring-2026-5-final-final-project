"""Tests for seed.py — @Hanson.

Uses mongomock so no live MongoDB is required.
Patches seed.MongoClient (the module-local reference) rather than
pymongo.MongoClient, which is the correct target after the module's
`from pymongo import MongoClient` import has already bound the name.
"""

import importlib.util
import os
from datetime import datetime
from unittest.mock import patch

import mongomock
import pytest

SEED_PATH = os.path.join(os.path.dirname(__file__), "..", "seed.py")


def _load_seed():
    """Load a fresh copy of seed.py on every call so patches don't bleed."""
    spec = importlib.util.spec_from_file_location("seed", SEED_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_seed(db_name="pennywise_test"):
    """Run seed.run() against a fresh mongomock database; return (seed, client)."""
    seed = _load_seed()
    client = mongomock.MongoClient()
    with patch.object(seed, "MongoClient", return_value=client), \
         patch.object(seed, "DB_NAME", db_name):
        seed.run()
    return seed, client


# ── Insertion counts ──────────────────────────────────────────────────────

def test_seed_inserts_two_users():
    _, client = _run_seed("pw_users")
    assert client["pw_users"]["users"].count_documents({}) == 2


def test_seed_inserts_seven_categories():
    _, client = _run_seed("pw_cats")
    assert client["pw_cats"]["categories"].count_documents({}) == 7


def test_seed_inserts_transactions():
    # 2 users × 3 months × (2 income + 8 expense) = 60
    _, client = _run_seed("pw_tx")
    assert client["pw_tx"]["transactions"].count_documents({}) == 60


def test_seed_inserts_eight_budgets():
    # 2 users × 4 budget categories
    _, client = _run_seed("pw_bud")
    assert client["pw_bud"]["budgets"].count_documents({}) == 8


# ── Idempotency ───────────────────────────────────────────────────────────

def test_seed_idempotent():
    """Running seed twice must not double the row count."""
    seed = _load_seed()
    client = mongomock.MongoClient()
    with patch.object(seed, "MongoClient", return_value=client), \
         patch.object(seed, "DB_NAME", "pw_idem"):
        seed.run()
        seed.run()

    db = client["pw_idem"]
    assert db["users"].count_documents({}) == 2
    assert db["categories"].count_documents({}) == 7


# ── Schema validation ─────────────────────────────────────────────────────

def test_users_have_required_fields():
    _, client = _run_seed("pw_ufields")
    for user in client["pw_ufields"]["users"].find():
        assert "username" in user
        assert "email" in user
        assert "password" in user
        assert "created_at" in user


def test_transactions_have_required_fields():
    _, client = _run_seed("pw_txfields")
    for tx in client["pw_txfields"]["transactions"].find():
        assert "type" in tx
        assert "amount" in tx
        assert "category" in tx
        assert "date" in tx
        assert tx["type"] in ("income", "expense")
        assert tx["amount"] > 0


def test_transactions_have_user_id():
    _, client = _run_seed("pw_txuid")
    for tx in client["pw_txuid"]["transactions"].find():
        assert "user_id" in tx


def test_budgets_have_required_fields():
    _, client = _run_seed("pw_bfields")
    for b in client["pw_bfields"]["budgets"].find():
        assert "category" in b
        assert "limit" in b
        assert "month" in b
        assert b["limit"] > 0


def test_budgets_have_user_id():
    _, client = _run_seed("pw_buid")
    for b in client["pw_buid"]["budgets"].find():
        assert "user_id" in b


def test_budget_month_format():
    _, client = _run_seed("pw_bmonth")
    import re
    for b in client["pw_bmonth"]["budgets"].find():
        assert re.match(r"^\d{4}-\d{2}$", b["month"])


def test_users_have_unique_usernames():
    _, client = _run_seed("pw_unique")
    usernames = [u["username"] for u in client["pw_unique"]["users"].find()]
    assert len(usernames) == len(set(usernames))


# ── Helper functions ──────────────────────────────────────────────────────

def test_tx_helper_expense():
    seed = _load_seed()
    tx = seed._tx("expense", 50.0, "food", datetime(2026, 4, 1))
    assert tx["type"] == "expense"
    assert tx["amount"] == 50.0
    assert tx["category"] == "food"
    assert tx["date"] == "2026-04-01"
    assert "user_id" not in tx


def test_tx_helper_income():
    seed = _load_seed()
    tx = seed._tx("income", 3000.0, "salary", datetime(2026, 4, 1))
    assert tx["type"] == "income"
    assert tx["amount"] == 3000.0


def test_tx_helper_with_user_id():
    from bson import ObjectId
    seed = _load_seed()
    uid = ObjectId()
    tx = seed._tx("expense", 20.0, "transport", datetime(2026, 4, 5), uid)
    assert tx["user_id"] == uid


def test_now_helper_is_iso_string():
    seed = _load_seed()
    ts = seed._now()
    assert isinstance(ts, str)
    assert "T" in ts


def test_month_start_helper_no_overflow():
    seed = _load_seed()
    # December + 2 months should land on February of the next year
    base = datetime(2026, 12, 1)
    result = seed._month_start(base, 2)
    assert result == datetime(2027, 2, 1)


def test_month_start_helper_same_month():
    seed = _load_seed()
    base = datetime(2026, 3, 15)
    result = seed._month_start(base, 0)
    assert result == datetime(2026, 3, 1)
