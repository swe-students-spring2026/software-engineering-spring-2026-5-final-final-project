"""Minimal MongoDB client utilities for the project."""

from typing import Iterable, List, Optional
import os
from pymongo import MongoClient


def get_client(mongo_uri: Optional[str] = None) -> MongoClient:
    uri = mongo_uri or os.getenv("MONGO_URI", "mongodb://mongo:27017")
    return MongoClient(uri, serverSelectionTimeoutMS=5000)


def seed_sample_data(client: MongoClient, db_name: str = "stocks_db") -> None:
    db = client[db_name]
    tickers = db.tickers
    tickers.create_index("Ticker", unique=True)
    sample = [
        {"Ticker": "AAPL", "Company": "Apple Inc.", "sector": "Technology"},
        {"Ticker": "MSFT", "Company": "Microsoft Corp.", "sector": "Technology"},
        {"Ticker": "TSLA", "Company": "Tesla, Inc.", "sector": "Automotive"},
    ]
    for doc in sample:
        tickers.update_one({"Ticker": doc["Ticker"]}, {"$set": doc}, upsert=True)

    sessions = db.sessions
    sessions.insert_one({"run": "seed", "status": "ok"})


def clear_db(client: MongoClient, db_name: str = "stocks_db") -> None:
    client.drop_database(db_name)


def get_tickers(client: MongoClient, db_name: str = "stocks_db") -> List[dict]:
    db = client[db_name]
    return list(db.tickers.find({}, {"_id": 0}))
