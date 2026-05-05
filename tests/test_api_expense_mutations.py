import importlib
from types import SimpleNamespace

from bson import ObjectId


class FakeUsersCollection:
    def __init__(self, users):
        self.users_by_username = {user["username"]: user for user in users}
        self.users_by_id = {user["_id"]: user for user in users}

    def find_one(self, query):
        if "username" in query:
            return self.users_by_username.get(query["username"])
        if "_id" in query:
            return self.users_by_id.get(query["_id"])
        return None


class FakeExpensesCollection:
    """Supports the subset of operations the API uses on expenses."""

    def __init__(self):
        self.docs = {}

    def insert_one(self, doc):
        new_doc = dict(doc)
        new_doc["_id"] = ObjectId()
        self.docs[new_doc["_id"]] = new_doc
        return SimpleNamespace(inserted_id=new_doc["_id"])

    def find(self, query):
        user_ids = set()
        for condition in query.get("$or", []):
            user_ids.update(value for value in condition.values() if value is not None)
        return [
            doc
            for doc in self.docs.values()
            if doc["payer_id"] in user_ids or doc["debtor_id"] in user_ids
        ]

    def find_one(self, query):
        if "_id" in query:
            return self.docs.get(query["_id"])
        return None

    def update_one(self, query, update):
        doc = self.docs.get(query["_id"])
        if doc is None:
            return SimpleNamespace(modified_count=0)
        doc.update(update.get("$set", {}))
        return SimpleNamespace(modified_count=1)

    def delete_one(self, query):
        if query["_id"] in self.docs:
            del self.docs[query["_id"]]
            return SimpleNamespace(deleted_count=1)
        return SimpleNamespace(deleted_count=0)


def load_api_module(monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://example:27017/")
    monkeypatch.setenv("MONGO_DBNAME", "splitring_test")
    module = importlib.import_module("api.app")
    return importlib.reload(module)


def create_test_client(monkeypatch):
    api_module = load_api_module(monkeypatch)
    alice_id = ObjectId()
    bob_id = ObjectId()
    users = FakeUsersCollection(
        [
            {"_id": alice_id, "username": "alice"},
            {"_id": bob_id, "username": "bob"},
        ]
    )
    expenses = FakeExpensesCollection()
    api_module.db = {"users": users, "expenses": expenses}
    api_module.app.config["TESTING"] = True
    return api_module.app.test_client(), expenses, alice_id, bob_id


def _seed_expense(expenses, payer_id, debtor_id, total=30.0, owed=15.0):
    """Insert a fixture expense; return its id as a string."""
    from datetime import datetime, timezone

    inserted = expenses.insert_one(
        {
            "payer_id": payer_id,
            "debtor_id": debtor_id,
            "total_amount": total,
            "amount_owed": owed,
            "description": "dinner",
            "category": "food",
            "date": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
            "created_by": payer_id,
        }
    )
    return str(inserted.inserted_id)


# ---------- GET /api/expenses/<id> ----------

def test_get_expense_returns_400_for_invalid_id(monkeypatch):
    client, _, _, _ = create_test_client(monkeypatch)
    response = client.get("/api/expenses/not-an-objectid")
    assert response.status_code == 400


def test_get_expense_returns_404_when_missing(monkeypatch):
    client, _, _, _ = create_test_client(monkeypatch)
    response = client.get(f"/api/expenses/{ObjectId()}")
    assert response.status_code == 404


def test_get_expense_returns_200_with_payload(monkeypatch):
    client, expenses, alice_id, bob_id = create_test_client(monkeypatch)
    expense_id = _seed_expense(expenses, alice_id, bob_id)

    response = client.get(f"/api/expenses/{expense_id}")
    assert response.status_code == 200
    body = response.get_json()
    assert body["payer_username"] == "alice"
    assert body["debtor_username"] == "bob"
    assert body["amount_owed"] == 15.0


# ---------- PATCH /api/expenses/<id> ----------

def test_patch_expense_returns_400_for_invalid_id(monkeypatch):
    client, _, _, _ = create_test_client(monkeypatch)
    response = client.patch(
        "/api/expenses/garbage",
        json={"username": "alice", "description": "new"},
    )
    assert response.status_code == 400


def test_patch_expense_returns_400_when_username_missing(monkeypatch):
    client, expenses, alice_id, bob_id = create_test_client(monkeypatch)
    expense_id = _seed_expense(expenses, alice_id, bob_id)
    response = client.patch(f"/api/expenses/{expense_id}", json={"description": "x"})
    assert response.status_code == 400


def test_patch_expense_returns_403_for_non_creator(monkeypatch):
    client, expenses, alice_id, bob_id = create_test_client(monkeypatch)
    expense_id = _seed_expense(expenses, alice_id, bob_id)

    response = client.patch(
        f"/api/expenses/{expense_id}",
        json={"username": "bob", "description": "hacked"},
    )
    assert response.status_code == 403


def test_patch_expense_returns_400_for_empty_description(monkeypatch):
    client, expenses, alice_id, bob_id = create_test_client(monkeypatch)
    expense_id = _seed_expense(expenses, alice_id, bob_id)

    response = client.patch(
        f"/api/expenses/{expense_id}",
        json={"username": "alice", "description": "   "},
    )
    assert response.status_code == 400


def test_patch_expense_returns_400_for_invalid_amount_split(monkeypatch):
    client, expenses, alice_id, bob_id = create_test_client(monkeypatch)
    expense_id = _seed_expense(expenses, alice_id, bob_id)

    response = client.patch(
        f"/api/expenses/{expense_id}",
        json={"username": "alice", "total_amount": 10, "amount_owed": 20},
    )
    assert response.status_code == 400


def test_patch_expense_returns_400_with_no_fields_to_update(monkeypatch):
    client, expenses, alice_id, bob_id = create_test_client(monkeypatch)
    expense_id = _seed_expense(expenses, alice_id, bob_id)

    response = client.patch(
        f"/api/expenses/{expense_id}",
        json={"username": "alice"},
    )
    assert response.status_code == 400


def test_patch_expense_updates_fields_on_success(monkeypatch):
    client, expenses, alice_id, bob_id = create_test_client(monkeypatch)
    expense_id = _seed_expense(expenses, alice_id, bob_id)

    response = client.patch(
        f"/api/expenses/{expense_id}",
        json={
            "username": "alice",
            "description": "lunch",
            "total_amount": 40,
            "amount_owed": 20,
            "category": "food",
        },
    )
    assert response.status_code == 200

    saved = next(iter(expenses.docs.values()))
    assert saved["description"] == "lunch"
    assert saved["total_amount"] == 40.0
    assert saved["amount_owed"] == 20.0


# ---------- DELETE /api/expenses/<id> ----------

def test_delete_expense_returns_400_for_invalid_id(monkeypatch):
    client, _, _, _ = create_test_client(monkeypatch)
    response = client.delete("/api/expenses/garbage?username=alice")
    assert response.status_code == 400


def test_delete_expense_returns_400_when_username_missing(monkeypatch):
    client, expenses, alice_id, bob_id = create_test_client(monkeypatch)
    expense_id = _seed_expense(expenses, alice_id, bob_id)
    response = client.delete(f"/api/expenses/{expense_id}")
    assert response.status_code == 400


def test_delete_expense_returns_404_when_missing(monkeypatch):
    client, _, _, _ = create_test_client(monkeypatch)
    response = client.delete(f"/api/expenses/{ObjectId()}?username=alice")
    assert response.status_code == 404


def test_delete_expense_returns_403_for_non_creator(monkeypatch):
    client, expenses, alice_id, bob_id = create_test_client(monkeypatch)
    expense_id = _seed_expense(expenses, alice_id, bob_id)
    response = client.delete(f"/api/expenses/{expense_id}?username=bob")
    assert response.status_code == 403


def test_delete_expense_succeeds_for_creator(monkeypatch):
    client, expenses, alice_id, bob_id = create_test_client(monkeypatch)
    expense_id = _seed_expense(expenses, alice_id, bob_id)
    response = client.delete(f"/api/expenses/{expense_id}?username=alice")
    assert response.status_code == 200
    assert len(expenses.docs) == 0
