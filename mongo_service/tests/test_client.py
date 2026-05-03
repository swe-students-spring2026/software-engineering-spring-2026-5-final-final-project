import mongomock
import pytest
from mongo_service import client as mclient


@pytest.fixture
def mock_client(monkeypatch):
    mc = mongomock.MongoClient()
    monkeypatch.setattr(mclient, "get_client", lambda uri=None: mc)
    return mc


def test_seed_and_get_tickers(mock_client):
    client = mclient.get_client()
    assert client.list_database_names() == []
    mclient.seed_sample_data(client, db_name="test_db")
    names = client.list_database_names()
    assert "test_db" in names
    tickers = mclient.get_tickers(client, db_name="test_db")
    assert isinstance(tickers, list)
    assert any(d.get("Ticker") == "AAPL" for d in tickers)


def test_clear_db(mock_client):
    client = mclient.get_client()
    mclient.seed_sample_data(client, db_name="to_clear")
    assert "to_clear" in client.list_database_names()
    mclient.clear_db(client, db_name="to_clear")
    assert "to_clear" not in client.list_database_names()
