import importlib
import sys
from types import ModuleType


class FakeCollection:
    def __init__(self):
        self.index_calls = []

    def create_index(self, keys, **kwargs):
        self.index_calls.append((keys, kwargs))


class FakeDatabase:
    def __init__(self, existing):
        self.existing = list(existing)
        self.created_collections = []
        self.collections = {}

    def list_collection_names(self):
        return list(self.existing)

    def create_collection(self, name):
        self.created_collections.append(name)
        self.existing.append(name)
        self.collections.setdefault(name, FakeCollection())

    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = FakeCollection()
        return self.collections[name]


class FakeClient:
    def __init__(self, database):
        self.database = database

    def __getitem__(self, db_name):
        return self.database


def load_init_db_module(monkeypatch):
    fake_pymongo = ModuleType("pymongo")
    fake_pymongo.MongoClient = object
    monkeypatch.setitem(sys.modules, "pymongo", fake_pymongo)

    monkeypatch.setenv("MONGO_URI", "mongodb://example:27017/")
    monkeypatch.setenv("MONGO_DBNAME", "splitring_test")
    module = importlib.import_module("database.init_db")
    return importlib.reload(module)


def test_main_creates_missing_collections(monkeypatch):
    init_db = load_init_db_module(monkeypatch)
    fake_database = FakeDatabase(existing=["users"])

    monkeypatch.setattr(
        init_db, "MongoClient", lambda uri: FakeClient(fake_database)
    )

    init_db.main()

    assert fake_database.created_collections == [
        "friendships",
        "expenses",
        "payments",
    ]


def test_main_does_not_recreate_existing_collections(monkeypatch):
    init_db = load_init_db_module(monkeypatch)
    fake_database = FakeDatabase(
        existing=["users", "friendships", "expenses", "payments"]
    )

    monkeypatch.setattr(
        init_db, "MongoClient", lambda uri: FakeClient(fake_database)
    )

    init_db.main()

    assert fake_database.created_collections == []


def test_main_creates_expected_indexes(monkeypatch):
    init_db = load_init_db_module(monkeypatch)
    fake_database = FakeDatabase(existing=[])

    monkeypatch.setattr(
        init_db, "MongoClient", lambda uri: FakeClient(fake_database)
    )

    init_db.main()

    users_index_calls = fake_database["users"].index_calls
    friendships_index_calls = fake_database["friendships"].index_calls
    expenses_index_calls = fake_database["expenses"].index_calls
    payments_index_calls = fake_database["payments"].index_calls

    assert ("username", {"unique": True}) in users_index_calls
    assert ("email", {"unique": True, "sparse": True}) in users_index_calls

    assert (
        [("user1_id", 1), ("user2_id", 1)],
        {"unique": True},
    ) in friendships_index_calls
    assert ("status", {}) in friendships_index_calls

    assert ([("payer_id", 1), ("debtor_id", 1)], {}) in expenses_index_calls
    assert ([("created_at", -1)], {}) in expenses_index_calls

    assert ("from_user_id", {}) in payments_index_calls
    assert ([("created_at", -1)], {}) in payments_index_calls
