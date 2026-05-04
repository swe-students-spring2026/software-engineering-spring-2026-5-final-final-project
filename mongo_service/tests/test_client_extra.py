import mongomock
import pytest

from mongo_service import client as mclient


def test_get_client_uses_env(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "mongodb://example:27017")
    c = mclient.get_client()
    assert c is not None


def test_seed_snapshot_dir_idempotent(tmp_path):
    import json

    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    payload = [{"Ticker": "AAPL", "Company": "Apple Inc.", "sector": "Technology"}]
    (snapshot_dir / "tickers.json").write_text(json.dumps(payload), encoding="utf-8")

    mc = mongomock.MongoClient()
    dbname = "seed_test_db"
    mclient.clear_db(mc, db_name=dbname)
    mclient.seed_sample_data(mc, db_name=dbname, snapshot_dir=snapshot_dir)
    first = list(mc[dbname].tickers.find({}, {"_id": 0}))
    assert any(d.get("Ticker") == "AAPL" for d in first)
    mclient.seed_sample_data(mc, db_name=dbname, snapshot_dir=snapshot_dir)
    second = list(mc[dbname].tickers.find({}, {"_id": 0}))
    assert len(second) == len({d["Ticker"] for d in second})


def test_get_tickers_returns_list():
    mc = mongomock.MongoClient()
    mc["mydb"].tickers.insert_one({"Ticker": "FOO", "Company": "Foo Inc."})
    out = mclient.get_tickers(mc, db_name="mydb")
    assert isinstance(out, list)
    assert out[0]["Ticker"] == "FOO"
