import os
from pymongo import MongoClient


def get_tasks_collection():
    MONGO_URI = os.getenv("MONGO_URI")
    MONGO_DBNAME = os.getenv("DB_NAME")

    connection = MongoClient(MONGO_URI)
    db = connection[MONGO_DBNAME]

    return db["tasks"]
