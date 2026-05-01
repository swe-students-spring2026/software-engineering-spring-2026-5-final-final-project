"""Budget endpoints — CRUD and spending-vs-limit status."""

import datetime

from bson import ObjectId
from flask import Blueprint, jsonify, request

from backend.db import get_budgets_collection, get_collection

budgets_bp = Blueprint("budgets", __name__)

_REQUIRED = ["category", "limit", "month"]


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


@budgets_bp.route("", methods=["POST"])
def create_budget():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be JSON"}), 400

    for field in _REQUIRED:
        if field not in data or data[field] in [None, ""]:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    if not isinstance(data["limit"], (int, float)) or data["limit"] <= 0:
        return jsonify({"error": "limit must be a positive number"}), 400

    budgets = get_budgets_collection()
    result = budgets.insert_one(
        {
            "category": data["category"],
            "limit": float(data["limit"]),
            "month": data["month"],
            "created_at": datetime.datetime.utcnow().isoformat(),
        }
    )
    return jsonify({"message": "Budget created successfully", "budget_id": str(result.inserted_id)}), 201


@budgets_bp.route("", methods=["GET"])
def get_budgets():
    budgets = get_budgets_collection()
    result = [_serialize(b) for b in budgets.find()]
    return jsonify({"budgets": result}), 200


@budgets_bp.route("/<budget_id>", methods=["GET"])
def get_budget(budget_id):
    if not ObjectId.is_valid(budget_id):
        return jsonify({"error": "Invalid budget id"}), 400

    budgets = get_budgets_collection()
    doc = budgets.find_one({"_id": ObjectId(budget_id)})
    if not doc:
        return jsonify({"error": "Budget not found"}), 404

    return jsonify({"budget": _serialize(doc)}), 200


@budgets_bp.route("/<budget_id>", methods=["PUT"])
def update_budget(budget_id):
    if not ObjectId.is_valid(budget_id):
        return jsonify({"error": "Invalid budget id"}), 400

    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be JSON"}), 400

    for field in _REQUIRED:
        if field not in data or data[field] in [None, ""]:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    if not isinstance(data["limit"], (int, float)) or data["limit"] <= 0:
        return jsonify({"error": "limit must be a positive number"}), 400

    budgets = get_budgets_collection()
    result = budgets.update_one(
        {"_id": ObjectId(budget_id)},
        {"$set": {"category": data["category"], "limit": float(data["limit"]), "month": data["month"]}},
    )
    if result.matched_count == 0:
        return jsonify({"error": "Budget not found"}), 404

    return jsonify({"message": "Budget updated successfully"}), 200


@budgets_bp.route("/<budget_id>", methods=["DELETE"])
def delete_budget(budget_id):
    if not ObjectId.is_valid(budget_id):
        return jsonify({"error": "Invalid budget id"}), 400

    budgets = get_budgets_collection()
    result = budgets.delete_one({"_id": ObjectId(budget_id)})
    if result.deleted_count == 0:
        return jsonify({"error": "Budget not found"}), 404

    return jsonify({"message": "Budget deleted successfully"}), 200


@budgets_bp.route("/status", methods=["GET"])
def budget_status():
    """Compare actual spending against each budget limit for its month."""
    budgets = get_budgets_collection()
    transactions = get_collection()

    all_budgets = list(budgets.find())
    if not all_budgets:
        return jsonify({"status": []}), 200

    # Build a lookup: (month, category) -> total spent
    pipeline = [
        {"$match": {"type": "expense"}},
        {
            "$project": {
                "category": 1,
                "amount": 1,
                "month": {"$substr": ["$date", 0, 7]},
            }
        },
        {
            "$group": {
                "_id": {"month": "$month", "category": "$category"},
                "total_spent": {"$sum": "$amount"},
            }
        },
    ]
    spent_map = {}
    for row in transactions.aggregate(pipeline):
        key = (row["_id"]["month"], row["_id"]["category"])
        spent_map[key] = row["total_spent"]

    result = []
    for b in all_budgets:
        key = (b["month"], b["category"])
        spent = spent_map.get(key, 0.0)
        limit = b["limit"]
        result.append(
            {
                "budget_id": str(b["_id"]),
                "category": b["category"],
                "month": b["month"],
                "limit": limit,
                "spent": spent,
                "remaining": round(limit - spent, 2),
                "over_budget": spent > limit,
            }
        )

    return jsonify({"status": result}), 200
