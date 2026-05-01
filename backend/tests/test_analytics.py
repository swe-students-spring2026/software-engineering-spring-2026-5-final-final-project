"""Tests for analytics API endpoints."""

from datetime import datetime

from bson import ObjectId

from backend.app import create_app


class FakeCollection:
    """Fake MongoDB collection returning predefined transaction records."""

    def __init__(self, records=None):
        self.records = records or []

    def find(self):
        return [dict(r) for r in self.records]


SAMPLE_RECORDS = [
    {
        "_id": ObjectId(),
        "type": "expense",
        "amount": 50.0,
        "category": "food",
        "description": "groceries",
        "date": datetime(2026, 1, 15),
    },
    {
        "_id": ObjectId(),
        "type": "expense",
        "amount": 30.0,
        "category": "transport",
        "description": "uber",
        "date": datetime(2026, 1, 20),
    },
    {
        "_id": ObjectId(),
        "type": "income",
        "amount": 3000.0,
        "category": "salary",
        "description": "monthly pay",
        "date": datetime(2026, 1, 1),
    },
    {
        "_id": ObjectId(),
        "type": "expense",
        "amount": 100.0,
        "category": "food",
        "description": "dining out",
        "date": datetime(2026, 2, 10),
    },
    {
        "_id": ObjectId(),
        "type": "income",
        "amount": 3000.0,
        "category": "salary",
        "description": "monthly pay",
        "date": datetime(2026, 2, 1),
    },
]


def _patch_collection(monkeypatch, records=None):
    """Helper to monkeypatch get_collection with a fake."""
    fake = FakeCollection(records if records is not None else SAMPLE_RECORDS)
    monkeypatch.setattr("backend.analytics.get_collection", lambda: fake)


# ---------- monthly-summary ----------


def test_monthly_summary_with_data(monkeypatch):
    _patch_collection(monkeypatch)

    app = create_app()
    client = app.test_client()
    resp = client.get("/api/analytics/monthly-summary")
    data = resp.get_json()

    assert resp.status_code == 200
    assert len(data["monthly_summary"]) == 2

    jan = next(m for m in data["monthly_summary"] if m["month"] == "2026-01")
    assert jan["income"] == 3000.0
    assert jan["expense"] == 80.0
    assert jan["net"] == 2920.0


def test_monthly_summary_empty(monkeypatch):
    _patch_collection(monkeypatch, records=[])

    app = create_app()
    client = app.test_client()
    resp = client.get("/api/analytics/monthly-summary")

    assert resp.status_code == 200
    assert resp.get_json()["monthly_summary"] == []


# ---------- spending-trends ----------


def test_spending_trends_with_data(monkeypatch):
    _patch_collection(monkeypatch)

    app = create_app()
    client = app.test_client()
    resp = client.get("/api/analytics/spending-trends")
    data = resp.get_json()

    assert resp.status_code == 200
    assert len(data["spending_trends"]) == 2

    jan = next(t for t in data["spending_trends"] if t["month"] == "2026-01")
    assert jan["total_spent"] == 80.0
    assert jan["change_pct"] is None  # first month has no prior

    feb = next(t for t in data["spending_trends"] if t["month"] == "2026-02")
    assert feb["total_spent"] == 100.0
    assert feb["change_pct"] == 25.0


def test_spending_trends_empty(monkeypatch):
    _patch_collection(monkeypatch, records=[])

    app = create_app()
    client = app.test_client()
    resp = client.get("/api/analytics/spending-trends")

    assert resp.status_code == 200
    assert resp.get_json()["spending_trends"] == []


def test_spending_trends_income_only(monkeypatch):
    income_only = [r for r in SAMPLE_RECORDS if r["type"] == "income"]
    _patch_collection(monkeypatch, records=income_only)

    app = create_app()
    client = app.test_client()
    resp = client.get("/api/analytics/spending-trends")

    assert resp.status_code == 200
    assert resp.get_json()["spending_trends"] == []


# ---------- top-categories ----------


def test_top_categories_with_data(monkeypatch):
    _patch_collection(monkeypatch)

    app = create_app()
    client = app.test_client()
    resp = client.get("/api/analytics/top-categories")
    data = resp.get_json()

    assert resp.status_code == 200
    assert len(data["top_categories"]) == 2

    top = data["top_categories"][0]
    assert top["category"] == "food"
    assert top["total_spent"] == 150.0
    assert top["percentage"] == 83.33

    second = data["top_categories"][1]
    assert second["category"] == "transport"
    assert second["total_spent"] == 30.0
    assert second["percentage"] == 16.67


def test_top_categories_empty(monkeypatch):
    _patch_collection(monkeypatch, records=[])

    app = create_app()
    client = app.test_client()
    resp = client.get("/api/analytics/top-categories")

    assert resp.status_code == 200
    assert resp.get_json()["top_categories"] == []


def test_top_categories_income_only(monkeypatch):
    income_only = [r for r in SAMPLE_RECORDS if r["type"] == "income"]
    _patch_collection(monkeypatch, records=income_only)

    app = create_app()
    client = app.test_client()
    resp = client.get("/api/analytics/top-categories")

    assert resp.status_code == 200
    assert resp.get_json()["top_categories"] == []


# ---------- integration: analytics still works with transactions ----------


def test_health_still_works_with_analytics():
    app = create_app()
    client = app.test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
