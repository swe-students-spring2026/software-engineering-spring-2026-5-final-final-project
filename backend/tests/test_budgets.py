"""Tests for budget endpoints — @kelaier."""

from bson import ObjectId

from backend.app import create_app


class FakeInsertResult:
    def __init__(self, oid=None):
        self.inserted_id = oid or ObjectId()


class FakeUpdateResult:
    def __init__(self, matched):
        self.matched_count = matched


class FakeDeleteResult:
    def __init__(self, deleted):
        self.deleted_count = deleted


class FakeBudgetsCollection:
    def __init__(self):
        self._oid = ObjectId()
        self._doc = {
            "_id": self._oid,
            "category": "food",
            "limit": 300.0,
            "month": "2026-04",
            "created_at": "2026-04-01T00:00:00",
        }

    def find(self):
        return [dict(self._doc)]

    def find_one(self, query):
        if query.get("_id") == self._oid:
            return dict(self._doc)
        return None

    def insert_one(self, doc):
        return FakeInsertResult(self._oid)

    def update_one(self, query, update):
        if query.get("_id") == self._oid:
            self._doc.update(update["$set"])
            return FakeUpdateResult(1)
        return FakeUpdateResult(0)

    def delete_one(self, query):
        if query.get("_id") == self._oid:
            return FakeDeleteResult(1)
        return FakeDeleteResult(0)


class FakeTransactionsCollection:
    def aggregate(self, pipeline):
        return [
            {"_id": {"month": "2026-04", "category": "food"}, "total_spent": 120.0}
        ]


def _patch(monkeypatch, budgets=None, transactions=None):
    b = budgets or FakeBudgetsCollection()
    t = transactions or FakeTransactionsCollection()
    monkeypatch.setattr("backend.budgets.get_budgets_collection", lambda: b)
    monkeypatch.setattr("backend.budgets.get_collection", lambda: t)
    return b


def _app():
    return create_app()


def test_create_budget_success(monkeypatch):
    _patch(monkeypatch)
    resp = _app().test_client().post(
        "/api/budgets",
        json={"category": "food", "limit": 300, "month": "2026-04"},
    )
    assert resp.status_code == 201
    assert resp.get_json()["message"] == "Budget created successfully"


def test_create_budget_missing_field(monkeypatch):
    _patch(monkeypatch)
    resp = _app().test_client().post("/api/budgets", json={"category": "food", "limit": 300})
    assert resp.status_code == 400
    assert "Missing required field" in resp.get_json()["error"]


def test_create_budget_invalid_limit(monkeypatch):
    _patch(monkeypatch)
    resp = _app().test_client().post(
        "/api/budgets",
        json={"category": "food", "limit": -10, "month": "2026-04"},
    )
    assert resp.status_code == 400
    assert "positive" in resp.get_json()["error"]


def test_create_budget_bad_json(monkeypatch):
    _patch(monkeypatch)
    resp = _app().test_client().post("/api/budgets", data="bad", content_type="text/plain")
    assert resp.status_code == 400


def test_get_budgets(monkeypatch):
    fake = _patch(monkeypatch)
    resp = _app().test_client().get("/api/budgets")
    data = resp.get_json()
    assert resp.status_code == 200
    assert len(data["budgets"]) == 1
    assert data["budgets"][0]["category"] == "food"


def test_get_budget_success(monkeypatch):
    fake = _patch(monkeypatch)
    resp = _app().test_client().get(f"/api/budgets/{fake._oid}")
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["budget"]["month"] == "2026-04"


def test_get_budget_not_found(monkeypatch):
    _patch(monkeypatch)
    resp = _app().test_client().get(f"/api/budgets/{ObjectId()}")
    assert resp.status_code == 404


def test_get_budget_invalid_id(monkeypatch):
    _patch(monkeypatch)
    resp = _app().test_client().get("/api/budgets/bad-id")
    assert resp.status_code == 400


def test_update_budget_success(monkeypatch):
    fake = _patch(monkeypatch)
    resp = _app().test_client().put(
        f"/api/budgets/{fake._oid}",
        json={"category": "food", "limit": 400, "month": "2026-04"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["message"] == "Budget updated successfully"


def test_update_budget_not_found(monkeypatch):
    _patch(monkeypatch)
    resp = _app().test_client().put(
        f"/api/budgets/{ObjectId()}",
        json={"category": "food", "limit": 400, "month": "2026-04"},
    )
    assert resp.status_code == 404


def test_update_budget_invalid_limit(monkeypatch):
    fake = _patch(monkeypatch)
    resp = _app().test_client().put(
        f"/api/budgets/{fake._oid}",
        json={"category": "food", "limit": 0, "month": "2026-04"},
    )
    assert resp.status_code == 400


def test_update_budget_bad_json(monkeypatch):
    fake = _patch(monkeypatch)
    resp = _app().test_client().put(
        f"/api/budgets/{fake._oid}", data="bad", content_type="text/plain"
    )
    assert resp.status_code == 400


def test_delete_budget_success(monkeypatch):
    fake = _patch(monkeypatch)
    resp = _app().test_client().delete(f"/api/budgets/{fake._oid}")
    assert resp.status_code == 200
    assert resp.get_json()["message"] == "Budget deleted successfully"


def test_delete_budget_not_found(monkeypatch):
    _patch(monkeypatch)
    resp = _app().test_client().delete(f"/api/budgets/{ObjectId()}")
    assert resp.status_code == 404


def test_delete_budget_invalid_id(monkeypatch):
    _patch(monkeypatch)
    resp = _app().test_client().delete("/api/budgets/bad-id")
    assert resp.status_code == 400


def test_budget_status(monkeypatch):
    _patch(monkeypatch)
    resp = _app().test_client().get("/api/budgets/status")
    data = resp.get_json()
    assert resp.status_code == 200
    row = data["status"][0]
    assert row["category"] == "food"
    assert row["spent"] == 120.0
    assert row["remaining"] == 180.0
    assert row["over_budget"] is False


def test_budget_status_empty(monkeypatch):
    class EmptyBudgets:
        def find(self):
            return []

    monkeypatch.setattr("backend.budgets.get_budgets_collection", lambda: EmptyBudgets())
    monkeypatch.setattr("backend.budgets.get_collection", lambda: FakeTransactionsCollection())
    resp = _app().test_client().get("/api/budgets/status")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == []


def test_budget_status_over_budget(monkeypatch):
    class OverSpentTransactions:
        def aggregate(self, pipeline):
            return [{"_id": {"month": "2026-04", "category": "food"}, "total_spent": 500.0}]

    _patch(monkeypatch, transactions=OverSpentTransactions())
    resp = _app().test_client().get("/api/budgets/status")
    row = resp.get_json()["status"][0]
    assert row["over_budget"] is True
    assert row["remaining"] == -200.0
