import importlib

from pymongo.errors import DuplicateKeyError
from werkzeug.security import generate_password_hash


class InsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class FakeUsersCollection:
    def __init__(self):
        self.insert_result = InsertResult("new-user-id")
        self.insert_error = None
        self.find_one_result = None
        self.inserted_docs = []

    def insert_one(self, doc):
        if self.insert_error is not None:
            raise self.insert_error
        self.inserted_docs.append(doc)
        return self.insert_result

    def find_one(self, query):
        return self.find_one_result


def load_api_module(monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://example:27017/")
    monkeypatch.setenv("MONGO_DBNAME", "splitring_test")
    module = importlib.import_module("api.app")
    return importlib.reload(module)


def create_test_client(monkeypatch):
    api_module = load_api_module(monkeypatch)
    users = FakeUsersCollection()
    api_module.db = {"users": users}
    api_module.app.config["TESTING"] = True
    return api_module.app.test_client(), users


def test_create_user_returns_400_when_required_fields_missing(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    response = client.post("/api/users", json={"username": "", "password": ""})

    assert response.status_code == 400
    assert response.get_json()["error"] == "username and password are required"


def test_create_user_returns_201_on_success(monkeypatch):
    client, users = create_test_client(monkeypatch)
    response = client.post(
        "/api/users",
        json={"username": "alice", "password": "secret", "email": "a@test.com"},
    )

    assert response.status_code == 201
    assert response.get_json() == {"id": "new-user-id", "username": "alice"}
    assert users.inserted_docs[0]["username"] == "alice"


def test_create_user_returns_409_on_duplicate_user(monkeypatch):
    client, users = create_test_client(monkeypatch)
    users.insert_error = DuplicateKeyError("duplicate key error on username")

    response = client.post(
        "/api/users", json={"username": "alice", "password": "secret"}
    )

    assert response.status_code == 409
    assert response.get_json()["error"] == "username already taken"


def test_login_returns_400_when_required_fields_missing(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    response = client.post("/api/login", json={"username": "", "password": ""})

    assert response.status_code == 400
    assert response.get_json()["error"] == "username and password are required"


def test_login_returns_401_for_invalid_credentials(monkeypatch):
    client, users = create_test_client(monkeypatch)
    users.find_one_result = {
        "_id": "existing-user-id",
        "username": "alice",
        "password_hash": generate_password_hash("correct-password"),
    }

    response = client.post(
        "/api/login", json={"username": "alice", "password": "wrong-password"}
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "invalid credentials"


def test_login_returns_200_for_valid_credentials(monkeypatch):
    client, users = create_test_client(monkeypatch)
    users.find_one_result = {
        "_id": "existing-user-id",
        "username": "alice",
        "password_hash": generate_password_hash("secret"),
    }

    response = client.post(
        "/api/login", json={"username": "alice", "password": "secret"}
    )

    assert response.status_code == 200
    assert response.get_json() == {"id": "existing-user-id", "username": "alice"}
