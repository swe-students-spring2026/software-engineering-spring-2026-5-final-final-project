"""Initialize the SplitRing MongoDB database with collections and indexes."""

import os
from pymongo import MongoClient  # pylint: disable=import-error

MONGO_URI = os.environ["MONGO_URI"]
DB_NAME = os.environ.get("MONGO_DBNAME", "splitring")


def main():
    """Create required collections and indexes."""
    client = MongoClient(MONGO_URI)
    database = client[DB_NAME]

    existing = database.list_collection_names()

    if "users" not in existing:
        database.create_collection("users")

    if "friendships" not in existing:
        database.create_collection("friendships")

    if "expenses" not in existing:
        database.create_collection("expenses")

    if "payments" not in existing:
        database.create_collection("payments")

    # users: lookup by username for login, by email for invites
    database["users"].create_index("username", unique=True)
    database["users"].create_index("email", unique=True, sparse=True)

    # friendships: a pair (user1_id, user2_id) is unique; user1_id is always
    # the lexicographically smaller ObjectId so each friendship has one row
    database["friendships"].create_index(
        [("user1_id", 1), ("user2_id", 1)], unique=True
    )
    database["friendships"].create_index("user1_id")
    database["friendships"].create_index("user2_id")
    database["friendships"].create_index("status")

    # expenses: query by either side of the pair, and by date for graphs
    database["expenses"].create_index("payer_id")
    database["expenses"].create_index("debtor_id")
    database["expenses"].create_index([("payer_id", 1), ("debtor_id", 1)])
    database["expenses"].create_index("date")
    database["expenses"].create_index([("created_at", -1)])

    # payments: settlement records, query by either side
    database["payments"].create_index("from_user_id")
    database["payments"].create_index("to_user_id")
    database["payments"].create_index("date")
    database["payments"].create_index([("created_at", -1)])

    print("Database initialization complete.")

if __name__ == "__main__":
    main()
