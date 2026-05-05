import importlib
from types import SimpleNamespace


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
    def __init__(self):
        self.docs = []
        self.next_id = 1

    def insert_one(self, doc):
        new_doc = dict(doc)
        new_doc["_id"] = f"expense-{self.next_id}"
        self.next_id += 1
        self.docs.append(new_doc)
        return SimpleNamespace(inserted_id=new_doc["_id"])

    def find(self, query):
        user_ids = set()
        for condition in query.get("$or", []):
            user_ids.update(value for value in condition.values() if value is not None)

        matches = []
        for doc in self.docs:
            if doc["payer_id"] in user_ids or doc["debtor_id"] in user_ids:
                matches.append(doc)
        return matches


def load_api_module(monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://example:27017/")
    monkeypatch.setenv("MONGO_DBNAME", "splitring_test")
    module = importlib.import_module("api.app")
    return importlib.reload(module)


def create_test_client(monkeypatch):
    api_module = load_api_module(monkeypatch)
    users = FakeUsersCollection(
        [
            {"_id": "id-alice", "username": "alice"},
            {"_id": "id-bob", "username": "bob"},
            {"_id": "id-carol", "username": "carol"},
        ]
    )
    expenses = FakeExpensesCollection()
    api_module.db = {"users": users, "expenses": expenses}
    api_module.app.config["TESTING"] = True
    return api_module.app.test_client(), expenses


def test_create_expense_returns_400_when_required_fields_missing(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    response = client.post("/api/expenses", json={"payer_username": "", "debtor_username": ""})

    assert response.status_code == 400
    assert response.get_json()["error"] == "payer_username and debtor_username are required"


def test_create_expense_returns_201_on_success(monkeypatch):
    client, expenses = create_test_client(monkeypatch)
    response = client.post(
        "/api/expenses",
        json={
            "payer_username": "alice",
            "debtor_username": "bob",
            "total_amount": 30,
            "amount_owed": 15,
            "description": "dinner",
            "category": "food",
            "date": "2026-05-05T00:00:00Z",
        },
    )

    assert response.status_code == 201
    assert response.get_json()["payer_username"] == "alice"
    assert len(expenses.docs) == 1


def test_create_expense_returns_400_for_invalid_amounts(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    response = client.post(
        "/api/expenses",
        json={
            "payer_username": "alice",
            "debtor_username": "bob",
            "total_amount": 10,
            "amount_owed": 20,
            "description": "bad split",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "amount_owed cannot exceed total_amount"


def test_list_expenses_returns_400_when_username_missing(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    response = client.get("/api/expenses")

    assert response.status_code == 400
    assert response.get_json()["error"] == "username query param is required"


def test_list_expenses_returns_user_expenses(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    client.post(
        "/api/expenses",
        json={
            "payer_username": "alice",
            "debtor_username": "bob",
            "total_amount": 30,
            "amount_owed": 15,
            "description": "dinner",
        },
    )
    client.post(
        "/api/expenses",
        json={
            "payer_username": "carol",
            "debtor_username": "alice",
            "total_amount": 20,
            "amount_owed": 10,
            "description": "groceries",
        },
    )

    response = client.get("/api/expenses?username=alice")

    assert response.status_code == 200
    data = response.get_json()
    assert data["username"] == "alice"
    assert len(data["expenses"]) == 2
