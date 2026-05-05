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


class FakeFriendshipsCollection:
    def __init__(self):
        self.docs = []
        self.next_id = 1

    def update_one(self, query, update, upsert=False):
        for doc in self.docs:
            if (
                doc["user1_id"] == query["user1_id"]
                and doc["user2_id"] == query["user2_id"]
            ):
                return SimpleNamespace(upserted_id=None)

        if not upsert:
            return SimpleNamespace(upserted_id=None)

        new_doc = dict(update["$setOnInsert"])
        new_doc["_id"] = f"friendship-{self.next_id}"
        self.next_id += 1
        self.docs.append(new_doc)
        return SimpleNamespace(upserted_id=new_doc["_id"])

    def find(self, query):
        or_conditions = query.get("$or", [])
        if not or_conditions:
            return []

        user_ids = {condition.get("user1_id") for condition in or_conditions}
        user_ids.update(
            condition.get("user2_id") for condition in or_conditions
        )
        user_ids.discard(None)

        matches = []
        for doc in self.docs:
            if doc["user1_id"] in user_ids or doc["user2_id"] in user_ids:
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
    friendships = FakeFriendshipsCollection()
    api_module.db = {"users": users, "friendships": friendships}
    api_module.app.config["TESTING"] = True
    return api_module.app.test_client(), friendships


def test_create_friendship_returns_400_when_fields_missing(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    response = client.post("/api/friendships", json={"username": "", "friend_username": ""})

    assert response.status_code == 400
    assert response.get_json()["error"] == "username and friend_username are required"


def test_create_friendship_returns_400_when_payload_is_not_object(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    response = client.post("/api/friendships", json=["alice", "bob"])

    assert response.status_code == 400
    assert response.get_json()["error"] == "request body must be a JSON object"


def test_create_friendship_returns_400_for_self_friendship(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    response = client.post(
        "/api/friendships",
        json={"username": "alice", "friend_username": "alice"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "cannot create friendship with yourself"


def test_create_friendship_returns_404_when_user_missing(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    response = client.post(
        "/api/friendships",
        json={"username": "alice", "friend_username": "ghost"},
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "both users must exist"


def test_create_friendship_returns_201_and_accepted_status(monkeypatch):
    client, friendships = create_test_client(monkeypatch)
    response = client.post(
        "/api/friendships",
        json={"username": "alice", "friend_username": "bob"},
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["status"] == "accepted"
    assert len(friendships.docs) == 1
    # accepted_at should be set on creation now (not None)
    assert friendships.docs[0]["accepted_at"] is not None
    assert friendships.docs[0]["status"] == "accepted"


def test_create_friendship_returns_409_if_exists(monkeypatch):
    client, friendships = create_test_client(monkeypatch)
    client.post("/api/friendships", json={"username": "alice", "friend_username": "bob"})

    response = client.post(
        "/api/friendships",
        json={"username": "alice", "friend_username": "bob"},
    )

    assert response.status_code == 409
    assert response.get_json()["error"] == "friendship already exists"
    assert len(friendships.docs) == 1


def test_list_friendships_returns_400_when_username_missing(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    response = client.get("/api/friendships")

    assert response.status_code == 400
    assert response.get_json()["error"] == "username query param is required"


def test_list_friendships_returns_404_when_user_missing(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    response = client.get("/api/friendships?username=ghost")

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_list_friendships_returns_user_friendships(monkeypatch):
    client, _ = create_test_client(monkeypatch)
    client.post("/api/friendships", json={"username": "alice", "friend_username": "bob"})
    client.post("/api/friendships", json={"username": "alice", "friend_username": "carol"})

    response = client.get("/api/friendships?username=alice")

    assert response.status_code == 200
    data = response.get_json()
    assert data["username"] == "alice"
    friend_names = sorted(
        friendship["friend_username"] for friendship in data["friendships"]
    )
    assert friend_names == ["bob", "carol"]
    # All listed friendships should be in accepted status
    for friendship in data["friendships"]:
        assert friendship["status"] == "accepted"
