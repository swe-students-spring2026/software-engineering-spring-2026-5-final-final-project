import pytest
from app.main import app

@pytest.fixture
def client():
    from app.main import app
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client

def test_lateness_penalty(client, monkeypatch):
    from bson import ObjectId
    import app.main as app_module

    USER_ID = "69f4a33044e301353c9f2c1c"
    LATENESS_VALUES = [15, -5, 5, 0, -3, 18]

    class FakeUsersCollection:
        def find_one(self, query):
            return {"_id": ObjectId(USER_ID), "lateness": LATENESS_VALUES}
        def update_one(self, query, update, upsert=False):
            pass

    monkeypatch.setattr(app_module, "get_users_collection", lambda: FakeUsersCollection())

    response = client.get(f"/lateness_penalty/{USER_ID}")
    data = response.get_json()

    expected = sum(LATENESS_VALUES[-5:]) / len(LATENESS_VALUES[-5:])
    assert data["lateness_penalty"] == expected