import os
import mongomock
import pytest
from mongo_service import client as mclient


def test_get_client_uses_env(monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://example:27017")
    c = mclient.get_client()
    assert c is not None


def test_seed_sample_data_idempotent(monkeypatch):
    mc = mongomock.MongoClient()
    monkeypatch.setattr(mclient, "get_client", lambda uri=None: mc)
    dbname = "seed_test_db"
    mclient.clear_db(mc, db_name=dbname)
    mclient.seed_sample_data(mc, db_name=dbname)
    first = list(mc[dbname].tickers.find({}, {"_id": 0}))
    assert any(d.get("Ticker") == "AAPL" for d in first)
    mclient.seed_sample_data(mc, db_name=dbname)
    second = list(mc[dbname].tickers.find({}, {"_id": 0}))
    assert len(second) == len({d["Ticker"] for d in second})


def test_get_tickers_returns_list(monkeypatch):
    mc = mongomock.MongoClient()
    mc["mydb"].tickers.insert_one({"Ticker": "FOO", "Company": "Foo Inc."})
    monkeypatch.setattr(mclient, "get_client", lambda uri=None: mc)
    out = mclient.get_tickers(mc, db_name="mydb")
    assert isinstance(out, list)
    assert out[0]["Ticker"] == "FOO"
