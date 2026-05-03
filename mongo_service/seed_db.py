"""Seed the MongoDB with starter data.
Run inside container or locally with appropriate env vars set.
"""

import os
import sys
from pymongo import MongoClient
from mongo_service.client import seed_sample_data, get_client


def main():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://mongo:27017")
    db_name = os.getenv("MONGO_DB", "stocks_db")
    try:
        client = get_client(mongo_uri)
        client.server_info()
    except Exception as exc:
        print(f"Failed to connect to MongoDB at {mongo_uri}: {exc}")
        sys.exit(2)

    print(f"Seeding database '{db_name}' at {mongo_uri}...")
    seed_sample_data(client, db_name=db_name)
    print("Done.")


if __name__ == "__main__":
    main()
