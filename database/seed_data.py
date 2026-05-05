"""Seed the database with sample data for local development."""

import os
from datetime import datetime, timezone

from pymongo import MongoClient  # pylint: disable=import-error
from werkzeug.security import generate_password_hash

MONGO_URI = os.environ["MONGO_URI"]
DB_NAME = os.environ.get("MONGO_DBNAME", "splitring")

SAMPLE_USERS = [
    {
        "username": "alice",
        "full_name": "Alice Johnson",
        "email": "alice@example.com",
        "password": "alice123",
    },
    {
        "username": "bob",
        "full_name": "Bob Lee",
        "email": "bob@example.com",
        "password": "bob123",
    },
    {
        "username": "carol",
        "full_name": "Carol Kim",
        "email": "carol@example.com",
        "password": "carol123",
    },
]

SAMPLE_FRIENDSHIPS = [("alice", "bob"), ("alice", "carol"), ("bob", "carol")]


def ordered_pair_ids(first_id, second_id):
    """Return the pair in stable lexicographic order."""
    if str(first_id) <= str(second_id):
        return first_id, second_id
    return second_id, first_id


def seed_users(database, now):
    """Upsert sample users and return IDs plus insert count."""
    users_collection = database["users"]
    user_ids = {}
    inserted = 0

    for user in SAMPLE_USERS:
        result = users_collection.update_one(
            {"username": user["username"]},
            {
                "$setOnInsert": {
                    "username": user["username"],
                    "full_name": user["full_name"],
                    "email": user["email"],
                    "password_hash": generate_password_hash(user["password"]),
                    "created_at": now,
                }
            },
            upsert=True,
        )
        if getattr(result, "upserted_id", None) is not None:
            inserted += 1

        saved_user = users_collection.find_one({"username": user["username"]})
        user_ids[user["username"]] = saved_user["_id"]

    return user_ids, inserted


def seed_friendships(database, user_ids, now):
    """Upsert accepted friendships for sample users."""
    friendships_collection = database["friendships"]
    inserted = 0

    for requester_username, target_username in SAMPLE_FRIENDSHIPS:
        requester_id = user_ids[requester_username]
        target_id = user_ids[target_username]
        user1_id, user2_id = ordered_pair_ids(requester_id, target_id)

        result = friendships_collection.update_one(
            {"user1_id": user1_id, "user2_id": user2_id},
            {
                "$setOnInsert": {
                    "user1_id": user1_id,
                    "user2_id": user2_id,
                    "status": "accepted",
                    "requested_by": requester_id,
                    "requested_at": now,
                    "accepted_at": now,
                }
            },
            upsert=True,
        )
        if getattr(result, "upserted_id", None) is not None:
            inserted += 1

    return inserted


def seed_database(database):
    """Seed all starter data and return a summary."""
    now = datetime.now(timezone.utc)
    user_ids, users_inserted = seed_users(database, now)
    friendships_inserted = seed_friendships(database, user_ids, now)
    return {
        "users_inserted": users_inserted,
        "friendships_inserted": friendships_inserted,
    }


def main():
    """Run seeding against configured MongoDB."""
    client = MongoClient(MONGO_URI)
    database = client[DB_NAME]
    summary = seed_database(database)
    print(
        "Seed data complete. "
        f"users_inserted={summary['users_inserted']} "
        f"friendships_inserted={summary['friendships_inserted']}"
    )
    client.close()


if __name__ == "__main__":
    main()
