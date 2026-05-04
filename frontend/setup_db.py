from app import app
from db import mongo

with app.app_context():
    # users: unique email and username
    mongo.db.users.create_index("email", unique=True)
    mongo.db.users.create_index("username", unique=True)

    # watchlists: one entry per user+movie, fast lookup by user
    mongo.db.watchlists.create_index([("user_id", 1), ("movie_id", 1)], unique=True)
    mongo.db.watchlists.create_index("user_id")

    # history: fast lookup by user, newest first
    mongo.db.history.create_index([("user_id", 1), ("timestamp", -1)])

    print("Collections and indexes created:")
    for name in mongo.db.list_collection_names():
        print(f"  {name}")
