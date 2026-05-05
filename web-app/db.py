import os
import certifi
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from bson import ObjectId

# Get MongoDB URI and DB name from environment variables
def get_mongo_uri() -> str:
    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        raise RuntimeError("MONGODB_URI not set in .env file")
    return mongo_uri

def get_db_name() -> str:
    return os.getenv("MONGODB_DB_NAME", "prioritymanager")

def get_client() -> MongoClient:
    return MongoClient(
        get_mongo_uri(),
        tlsCAFile=certifi.where()
    )

def get_database() -> Database:
    client = get_client()
    return client[get_db_name()]

def users_collection() -> Collection:
    return get_database()["users"]

def tasks_collection() -> Collection:
    return get_database()["tasks"]

# Create database indexes
def create_indexes() -> None:
    users = users_collection()
    tasks = tasks_collection()

    # Ensure unique users and email fields
    users.create_index([("username", 1)], unique=True)
    users.create_index([("email", 1)], unique=True)

    # Indexes for task priority and status
    tasks.create_index([("user_id", 1)])
    tasks.create_index([("priority", 1)])
    tasks.create_index([("status", 1)])
    tasks.create_index([("created_at", -1)])

def build_user_document(username: str, email: str, hashed_password: str) -> dict:
    return {
        "username": username.strip(),
        "email": email.strip().lower(),
        "password": hashed_password,
        "created_at": datetime.now(timezone.utc),
    }

def build_task_document(user_id: str, title: str, description: str, priority: str) -> dict:
    return {
        "user_id": ObjectId(user_id),
        "title": title.strip(),
        "description": description.strip(),
        "priority": priority.strip().title(),
        "status": "Pending",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

def insert_user(username: str, email: str, hashed_password: str) -> str:
    user_doc = build_user_document(username, email, hashed_password)
    result = users_collection().insert_one(user_doc)
    return str(result.inserted_id)

def insert_task(user_id: str, title: str, description: str, priority: str) -> str:
    task_doc = build_task_document(user_id, title, description, priority)
    result = tasks_collection().insert_one(task_doc)
    return str(result.inserted_id)

def get_tasks_for_user(user_id: str) -> list:
    tasks = list(tasks_collection().find({"user_id": ObjectId(user_id)}))

    priority_order = {
        "High": 1,
        "Medium": 2,
        "Low": 3
    }

    tasks.sort(key=lambda task: priority_order.get(task.get("priority"), 99))

    return tasks

def mark_task_complete(task_id: str, user_id: str) -> bool:
    result = tasks_collection().update_one(
        {"_id": ObjectId(task_id), "user_id": ObjectId(user_id)},
        {"$set": {"status": "Complete", "updated_at": datetime.now(timezone.utc)}}
    )
    return result.modified_count == 1

def delete_task(task_id: str, user_id: str) -> bool:
    result = tasks_collection().delete_one({"_id": ObjectId(task_id), "user_id": ObjectId(user_id)})
    return result.deleted_count == 1

def find_user_by_username(username: str):
    """
    Finds a user by their username in the 'users' collection.
    """
    return users_collection().find_one({"username": username})

def find_user_by_id(user_id:str):
    return users_collection().find_one({"_id":ObjectId(user_id)})


def update_user_profile(user_id: str, username: str, email: str) -> bool:
    result = users_collection().update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {
                "username": username.strip(),
                "email": email.strip().lower(),
            }
        },
    )
    return result.modified_count == 1


def delete_user_profile(user_id: str) -> bool:
    tasks_collection().delete_many({"user_id": ObjectId(user_id)})
    result = users_collection().delete_one({"_id": ObjectId(user_id)})
    return result.deleted_count == 1