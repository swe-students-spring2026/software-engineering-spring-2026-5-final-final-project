"""Database helpers for accessing MongoDB collections."""

from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION_NAME

def get_collection():
    """
    Get the MongoDB collection for transactions.

    Returns:
        The MongoDB collection object.
    """
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]
    collection = db[MONGO_COLLECTION_NAME]
    return collection

def save_transaction(transaction: dict):
    """
    Save a transaction document to MongoDB.

    Args:
        transaction: A dictionary containing transaction data.

    Returns:
        The inserted MongoDB document ID.
    """
    if not isinstance(transaction, dict):
        raise ValueError("transaction must be a dictionary")

    collection = get_collection()
    result = collection.insert_one(transaction)
    return result.inserted_id
