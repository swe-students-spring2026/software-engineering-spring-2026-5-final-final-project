import importlib
from types import SimpleNamespace


class FakeCollection:
    def __init__(self):
        self.docs = {}
        self.next_id = 1

    def _key_from_filter(self, query):
        return tuple(sorted(query.items()))

    def update_one(self, query, update, upsert=False):
        key = self._key_from_filter(query)
        if key in self.docs:
            return SimpleNamespace(upserted_id=None)
        if not upsert:
            return SimpleNamespace(upserted_id=None)

        document = dict(query)
        document.update(update.get("$setOnInsert", {}))
        document["_id"] = f"id-{self.next_id}"
        self.next_id += 1
        self.docs[key] = document
        return SimpleNamespace(upserted_id=document["_id"])

    def find_one(self, query):
        key = self._key_from_filter(query)
        return self.docs.get(key)


class FakeDatabase:
    def __init__(self):
        self.collections = {
            "users": FakeCollection(),
            "friendships": FakeCollection(),
        }

    def __getitem__(self, name):
        return self.collections[name]


class FakeClient:
    def __init__(self, database):
        self.database = database
        self.closed = False

    def __getitem__(self, db_name):
        return self.database

    def close(self):
        self.closed = True


def load_seed_module(monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://example:27017/")
    monkeypatch.setenv("MONGO_DBNAME", "splitring_test")
    module = importlib.import_module("database.seed_data")
    return importlib.reload(module)


def test_seed_database_is_idempotent(monkeypatch):
    seed_data = load_seed_module(monkeypatch)
    fake_database = FakeDatabase()

    first_run = seed_data.seed_database(fake_database)
    second_run = seed_data.seed_database(fake_database)

    assert first_run == {"users_inserted": 3, "friendships_inserted": 3}
    assert second_run == {"users_inserted": 0, "friendships_inserted": 0}


def test_main_seeds_and_closes_client(monkeypatch):
    seed_data = load_seed_module(monkeypatch)
    fake_database = FakeDatabase()
    fake_client = FakeClient(fake_database)

    monkeypatch.setattr(seed_data, "MongoClient", lambda uri: fake_client)

    seed_data.main()

    assert fake_client.closed is True


def test_ordered_pair_ids_returns_stable_order(monkeypatch):
    seed_data = load_seed_module(monkeypatch)

    first, second = seed_data.ordered_pair_ids("id-z", "id-a")

    assert (first, second) == ("id-a", "id-z")
