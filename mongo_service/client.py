"""MongoDB client and snapshot import helpers."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import List, Optional

from pymongo import MongoClient


def _resolve_mongo_uri(mongo_uri: Optional[str] = None) -> str:
    if mongo_uri:
        return mongo_uri
    return os.getenv("MONGODB_URI") or os.getenv("MONGO_URI") or "mongodb://mongo:27017"


def get_client(mongo_uri: Optional[str] = None) -> MongoClient:
    uri = _resolve_mongo_uri(mongo_uri)
    return MongoClient(uri, serverSelectionTimeoutMS=5000)


def _load_json_records(path: Path) -> List[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [dict(item) for item in payload]
    if isinstance(payload, dict):
        for key in ("records", "documents", "items", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [dict(item) for item in value]
        return [dict(payload)]
    raise ValueError(f"Unsupported JSON structure in {path}")


def _load_csv_records(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _load_records(path: Path) -> List[dict]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return _load_json_records(path)
    if suffix == ".csv":
        return _load_csv_records(path)
    raise ValueError(f"Unsupported snapshot file type: {path}")


def import_snapshot_dir(
    client: MongoClient, db_name: str, snapshot_dir: str | Path
) -> List[str]:
    snapshot_path = Path(snapshot_dir)
    if not snapshot_path.exists():
        raise FileNotFoundError(f"Snapshot directory does not exist: {snapshot_path}")

    db = client[db_name]
    imported_collections: List[str] = []

    for path in sorted(snapshot_path.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".json", ".csv"}:
            continue

        records = _load_records(path)
        if not records:
            continue

        collection = db[path.stem]
        collection.drop()
        collection.insert_many(records)

        if path.stem == "tickers" and any("Ticker" in record for record in records):
            collection.create_index("Ticker", unique=True)

        imported_collections.append(path.stem)

    if not imported_collections:
        raise FileNotFoundError(
            f"No JSON or CSV snapshot files found in {snapshot_path}"
        )

    return imported_collections


def seed_sample_data(
    client: MongoClient,
    db_name: str = "stocks_db",
    snapshot_dir: str | Path | None = None,
) -> List[str]:
    directory = snapshot_dir or os.getenv("PIPELINE_OUTPUT_DIR") or "pipeline/output"
    return import_snapshot_dir(client, db_name=db_name, snapshot_dir=directory)


def clear_db(client: MongoClient, db_name: str = "stocks_db") -> None:
    client.drop_database(db_name)


def get_tickers(client: MongoClient, db_name: str = "stocks_db") -> List[dict]:
    db = client[db_name]
    return list(db.tickers.find({}, {"_id": 0}))
