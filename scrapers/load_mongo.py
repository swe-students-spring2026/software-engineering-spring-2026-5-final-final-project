"""One-shot script to clear the classes collection and reload from classes_example.json."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
DATA_PATH = Path(__file__).with_name("classes_example.json")


def parse_date(val: object) -> object:
    if isinstance(val, dict) and "$date" in val:
        raw = val["$date"].replace("Z", "+00:00")
        return datetime.fromisoformat(raw)
    return val


def prepare(doc: dict) -> dict:
    out = dict(doc)
    if "scraped_at" in out:
        out["scraped_at"] = parse_date(out["scraped_at"])
    # Normalize status capitalisation
    if "status" in out and isinstance(out["status"], str):
        s = out["status"]
        if s.lower() == "open":
            out["status"] = "Open"
    return out


def main() -> None:
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]

    with open(DATA_PATH, encoding="utf-8") as f:
        docs = [prepare(d) for d in json.load(f)]

    deleted = db.classes.delete_many({}).deleted_count
    print(f"Deleted {deleted} existing class documents.")

    result = db.classes.insert_many(docs, ordered=False)
    print(f"Inserted {len(result.inserted_ids)} class documents.")

    client.close()


if __name__ == "__main__":
    main()
