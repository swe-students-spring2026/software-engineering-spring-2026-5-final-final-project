"""Transaction routes for the PennyWise backend API."""

from bson import ObjectId
from flask import Blueprint, jsonify, request

from backend.db import get_collection, save_transaction


transactions_bp = Blueprint("transactions", __name__)


def serialize_transaction(transaction: dict):
    """
    Convert MongoDB document into JSON-friendly dictionary.
    """
    transaction["_id"] = str(transaction["_id"])
    return transaction


@transactions_bp.route("", methods=["POST"])
def create_transaction():
    """
    Create a transaction.
    """
    data = request.get_json()

    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be JSON"}), 400

    required_fields = ["type", "amount", "category", "date"]

    for field in required_fields:
        if field not in data or data[field] in [None, ""]:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    if data["type"] not in ["income", "expense"]:
        return jsonify({"error": "type must be income or expense"}), 400

    if not isinstance(data["amount"], (int, float)) or data["amount"] <= 0:
        return jsonify({"error": "amount must be a positive number"}), 400

    transaction = {
        "type": data["type"],
        "amount": data["amount"],
        "category": data["category"],
        "description": data.get("description", ""),
        "date": data["date"],
    }

    transaction_id = save_transaction(transaction)

    return jsonify(
        {
            "message": "Transaction created successfully",
            "transaction_id": str(transaction_id),
        }
    ), 201


@transactions_bp.route("", methods=["GET"])
def get_transactions():
    """
    Get all transactions.
    """
    collection = get_collection()
    transactions = collection.find()

    result = [serialize_transaction(transaction) for transaction in transactions]

    return jsonify({"transactions": result}), 200


@transactions_bp.route("/<transaction_id>", methods=["GET"])
def get_transaction(transaction_id):
    """
    Get one transaction by id.
    """
    if not ObjectId.is_valid(transaction_id):
        return jsonify({"error": "Invalid transaction id"}), 400

    collection = get_collection()
    transaction = collection.find_one({"_id": ObjectId(transaction_id)})

    if not transaction:
        return jsonify({"error": "Transaction not found"}), 404

    return jsonify({"transaction": serialize_transaction(transaction)}), 200


@transactions_bp.route("/<transaction_id>", methods=["PUT"])
def update_transaction(transaction_id):
    """
    Update one transaction by id.
    """
    if not ObjectId.is_valid(transaction_id):
        return jsonify({"error": "Invalid transaction id"}), 400

    data = request.get_json()

    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be JSON"}), 400

    required_fields = ["type", "amount", "category", "date"]

    for field in required_fields:
        if field not in data or data[field] in [None, ""]:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    if data["type"] not in ["income", "expense"]:
        return jsonify({"error": "type must be income or expense"}), 400

    if not isinstance(data["amount"], (int, float)) or data["amount"] <= 0:
        return jsonify({"error": "amount must be a positive number"}), 400

    updated_transaction = {
        "type": data["type"],
        "amount": data["amount"],
        "category": data["category"],
        "description": data.get("description", ""),
        "date": data["date"],
    }

    collection = get_collection()
    result = collection.update_one(
        {"_id": ObjectId(transaction_id)},
        {"$set": updated_transaction},
    )

    if result.matched_count == 0:
        return jsonify({"error": "Transaction not found"}), 404

    return jsonify({"message": "Transaction updated successfully"}), 200


@transactions_bp.route("/<transaction_id>", methods=["DELETE"])
def delete_transaction(transaction_id):
    """
    Delete a transaction by id.
    """
    if not ObjectId.is_valid(transaction_id):
        return jsonify({"error": "Invalid transaction id"}), 400

    collection = get_collection()
    result = collection.delete_one({"_id": ObjectId(transaction_id)})

    if result.deleted_count == 0:
        return jsonify({"error": "Transaction not found"}), 404

    return jsonify({"message": "Transaction deleted successfully"}), 200
