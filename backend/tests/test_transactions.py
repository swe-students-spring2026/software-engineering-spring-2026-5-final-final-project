"""Tests for transaction API endpoints."""

from bson import ObjectId

from backend.app import create_app


class FakeInsertResult:
    """Fake MongoDB insert result."""

    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class FakeDeleteResult:
    """Fake MongoDB delete result."""

    def __init__(self, deleted_count):
        self.deleted_count = deleted_count


class FakeUpdateResult:
    """Fake MongoDB update result."""

    def __init__(self, matched_count):
        self.matched_count = matched_count


class FakeCollection:
    """Fake MongoDB collection."""

    def __init__(self):
        self.record_id = ObjectId()
        self.record = {
            "_id": self.record_id,
            "type": "expense",
            "amount": 12.5,
            "category": "food",
            "description": "lunch",
            "date": "2026-04-27",
        }

    def find(self):
        return [self.record.copy()]

    def find_one(self, query):
        if query["_id"] == self.record_id:
            return self.record.copy()
        return None

    def update_one(self, query, update):
        if query["_id"] == self.record_id:
            self.record.update(update["$set"])
            return FakeUpdateResult(1)
        return FakeUpdateResult(0)

    def delete_one(self, query):
        if query["_id"] == self.record_id:
            return FakeDeleteResult(1)
        return FakeDeleteResult(0)


def test_health():
    """Test health endpoint."""
    flask_app = create_app()
    client = flask_app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_create_transaction_success(monkeypatch):
    """Test creating a transaction successfully."""
    fake_id = ObjectId()

    def fake_save_transaction(transaction):
        assert transaction["type"] == "expense"
        assert transaction["amount"] == 12.5
        assert transaction["category"] == "food"
        return fake_id

    monkeypatch.setattr("backend.transactions.save_transaction", fake_save_transaction)

    flask_app = create_app()
    client = flask_app.test_client()

    response = client.post(
        "/api/transactions",
        json={
            "type": "expense",
            "amount": 12.5,
            "category": "food",
            "description": "lunch",
            "date": "2026-04-27",
        },
    )

    data = response.get_json()

    assert response.status_code == 201
    assert data["message"] == "Transaction created successfully"
    assert data["transaction_id"] == str(fake_id)


def test_create_transaction_missing_field():
    """Test creating a transaction with missing data."""
    flask_app = create_app()
    client = flask_app.test_client()

    response = client.post(
        "/api/transactions",
        json={
            "type": "expense",
            "amount": 12.5,
            "category": "food",
        },
    )

    assert response.status_code == 400
    assert "Missing required field" in response.get_json()["error"]


def test_create_transaction_invalid_type():
    """Test creating a transaction with invalid type."""
    flask_app = create_app()
    client = flask_app.test_client()

    response = client.post(
        "/api/transactions",
        json={
            "type": "shopping",
            "amount": 12.5,
            "category": "food",
            "date": "2026-04-27",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "type must be income or expense"


def test_create_transaction_invalid_amount():
    """Test creating a transaction with invalid amount."""
    flask_app = create_app()
    client = flask_app.test_client()

    response = client.post(
        "/api/transactions",
        json={
            "type": "expense",
            "amount": -1,
            "category": "food",
            "date": "2026-04-27",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "amount must be a positive number"


def test_get_transactions(monkeypatch):
    """Test getting all transactions."""
    fake_collection = FakeCollection()

    def fake_get_collection():
        return fake_collection

    monkeypatch.setattr("backend.transactions.get_collection", fake_get_collection)

    flask_app = create_app()
    client = flask_app.test_client()

    response = client.get("/api/transactions")
    data = response.get_json()

    assert response.status_code == 200
    assert len(data["transactions"]) == 1
    assert data["transactions"][0]["type"] == "expense"


def test_get_transaction_success(monkeypatch):
    """Test getting one transaction."""
    fake_collection = FakeCollection()

    def fake_get_collection():
        return fake_collection

    monkeypatch.setattr("backend.transactions.get_collection", fake_get_collection)

    flask_app = create_app()
    client = flask_app.test_client()

    response = client.get(f"/api/transactions/{fake_collection.record_id}")
    data = response.get_json()

    assert response.status_code == 200
    assert data["transaction"]["category"] == "food"


def test_update_transaction_success(monkeypatch):
    """Test updating one transaction."""
    fake_collection = FakeCollection()

    def fake_get_collection():
        return fake_collection

    monkeypatch.setattr("backend.transactions.get_collection", fake_get_collection)

    flask_app = create_app()
    client = flask_app.test_client()

    response = client.put(
        f"/api/transactions/{fake_collection.record_id}",
        json={
            "type": "expense",
            "amount": 20,
            "category": "food",
            "description": "updated lunch",
            "date": "2026-04-27",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "Transaction updated successfully"


def test_delete_transaction_success(monkeypatch):
    """Test deleting one transaction."""
    fake_collection = FakeCollection()

    def fake_get_collection():
        return fake_collection

    monkeypatch.setattr("backend.transactions.get_collection", fake_get_collection)

    flask_app = create_app()
    client = flask_app.test_client()

    response = client.delete(f"/api/transactions/{fake_collection.record_id}")

    assert response.status_code == 200
    assert response.get_json()["message"] == "Transaction deleted successfully"


def test_delete_transaction_invalid_id():
    """Test deleting with invalid transaction id."""
    flask_app = create_app()
    client = flask_app.test_client()

    response = client.delete("/api/transactions/not-real-id")

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid transaction id"
