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


class FakePaymentsCollection:
    def __init__(self):
        self.docs = []
        self.next_id = 1

    def insert_one(self, doc):
        new_doc = dict(doc)
        new_doc["_id"] = f"payment-{self.next_id}"
        self.next_id += 1
        self.docs.append(new_doc)
        return SimpleNamespace(inserted_id=new_doc["_id"])

    def find(self, query):
        user_ids = set()
        for condition in query.get("$or", []):
            user_ids.update(value for value in condition.values() if value is not None)

        matches = []
        for doc in self.docs:
            if doc["from_user_id"] in user_ids or doc["to_user_id"] in user_ids:
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
    payments = FakePaymentsCollection()
    api_module.db = {"users": users, "payments": payments}
    api_module.app.config["TESTING"] = True
    return api_module.app.test_client(), payments


def test_create_payment_returns_400_when_required_fields_missing(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    response = client.post(
        "/api/payments",
        json={"from_username": "", "to_username": ""},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "from_username and to_username are required"


def test_create_payment_returns_400_when_payload_is_not_object(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    response = client.post("/api/payments", json=["alice", "bob"])

    assert response.status_code == 400


def test_create_payment_returns_400_for_self_payment(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    response = client.post(
        "/api/payments",
        json={"from_username": "alice", "to_username": "alice", "amount": 10},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "from and to users must be different"


def test_create_payment_returns_400_for_non_numeric_amount(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    response = client.post(
        "/api/payments",
        json={"from_username": "alice", "to_username": "bob", "amount": "not-a-number"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "amount must be numeric"


def test_create_payment_returns_400_for_zero_amount(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    response = client.post(
        "/api/payments",
        json={"from_username": "alice", "to_username": "bob", "amount": 0},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "amount must be greater than zero"


def test_create_payment_returns_400_for_bad_date(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    response = client.post(
        "/api/payments",
        json={
            "from_username": "alice",
            "to_username": "bob",
            "amount": 10,
            "date": "not-a-date",
        },
    )

    assert response.status_code == 400


def test_create_payment_returns_404_when_user_missing(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    response = client.post(
        "/api/payments",
        json={"from_username": "alice", "to_username": "ghost", "amount": 10},
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "both users must exist"


def test_create_payment_returns_201_on_success(monkeypatch):
    client, payments = create_test_client(monkeypatch)
    response = client.post(
        "/api/payments",
        json={
            "from_username": "alice",
            "to_username": "bob",
            "amount": 25.50,
            "note": "Venmo",
            "date": "2026-05-05T00:00:00Z",
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["from_username"] == "alice"
    assert body["to_username"] == "bob"
    assert body["amount"] == 25.50
    assert len(payments.docs) == 1


def test_list_payments_returns_400_when_username_missing(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    response = client.get("/api/payments")

    assert response.status_code == 400


def test_list_payments_returns_404_when_user_missing(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    response = client.get("/api/payments?username=ghost")

    assert response.status_code == 404


def test_list_payments_returns_user_payments(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    client.post(
        "/api/payments",
        json={"from_username": "alice", "to_username": "bob", "amount": 10},
    )
    client.post(
        "/api/payments",
        json={"from_username": "carol", "to_username": "alice", "amount": 20},
    )

    response = client.get("/api/payments?username=alice")

    assert response.status_code == 200
    data = response.get_json()
    assert data["username"] == "alice"
    assert len(data["payments"]) == 2
