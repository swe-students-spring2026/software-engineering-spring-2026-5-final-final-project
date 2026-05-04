import json

import mongomock
import pytest

from mongo_service import client as mclient


@pytest.fixture
def mock_client(monkeypatch):
    mc = mongomock.MongoClient()
    monkeypatch.setattr(mclient, "get_client", lambda uri=None: mc)
    return mc


def test_seed_and_get_tickers(mock_client, tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    (snapshot_dir / "tickers.json").write_text(
        json.dumps(
            [
                {"Ticker": "AAPL", "Company": "Apple Inc.", "sector": "Technology"},
                {
                    "Ticker": "MSFT",
                    "Company": "Microsoft Corp.",
                    "sector": "Technology",
                },
            ]
        ),
        encoding="utf-8",
    )
    (snapshot_dir / "sessions.csv").write_text(
        "run,status\nseed,ok\n", encoding="utf-8"
    )

    client = mclient.get_client()
    assert client.list_database_names() == []
    mclient.seed_sample_data(client, db_name="test_db", snapshot_dir=snapshot_dir)
    names = client.list_database_names()
    assert "test_db" in names
    tickers = mclient.get_tickers(client, db_name="test_db")
    assert isinstance(tickers, list)
    assert any(d.get("Ticker") == "AAPL" for d in tickers)


def test_clear_db(mock_client, tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    (snapshot_dir / "tickers.json").write_text(
        json.dumps(
            [{"Ticker": "TSLA", "Company": "Tesla, Inc.", "sector": "Automotive"}]
        ),
        encoding="utf-8",
    )

    client = mclient.get_client()
    mclient.seed_sample_data(client, db_name="to_clear", snapshot_dir=snapshot_dir)
    assert "to_clear" in client.list_database_names()
    mclient.clear_db(client, db_name="to_clear")
    assert "to_clear" not in client.list_database_names()
