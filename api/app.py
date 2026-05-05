import os
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DBNAME", "splitring")]


def ordered_pair_ids(first_id, second_id):
    """Return a deterministic pair order for friendship uniqueness."""
    if str(first_id) <= str(second_id):
        return first_id, second_id
    return second_id, first_id


def get_json_object():
    """Parse request JSON and ensure the payload is an object."""
    data = request.get_json(silent=True)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        return None
    return data


def parse_iso_datetime(value):
    """Parse ISO datetime strings and keep timezone-aware values."""
    if not value:
        return datetime.now(timezone.utc)
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


@app.route("/api/users", methods=["POST"])
def create_user():
    data = get_json_object()
    if data is None:
        return jsonify({"error": "request body must be a JSON object"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    email_raw = data.get("email") or ""
    email = email_raw.strip() or None

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    user = {
        "username": username,
        "password_hash": generate_password_hash(password),
        "created_at": datetime.now(timezone.utc),
    }
    if email is not None:
        user["email"] = email

    try:
        result = db["users"].insert_one(user)
    except DuplicateKeyError as e:
        key = "email" if "email" in str(e) else "username"
        return jsonify({"error": f"{key} already taken"}), 409

    return jsonify({"id": str(result.inserted_id), "username": username}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = get_json_object()
    if data is None:
        return jsonify({"error": "request body must be a JSON object"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    user = db["users"].find_one({"username": username})
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "invalid credentials"}), 401

    return jsonify({"id": str(user["_id"]), "username": user["username"]}), 200


@app.route("/api/friendships", methods=["POST"])
def create_friendship():
    data = get_json_object()
    if data is None:
        return jsonify({"error": "request body must be a JSON object"}), 400

    username = data.get("username", "").strip()
    friend_username = data.get("friend_username", "").strip()

    if not username or not friend_username:
        return jsonify({"error": "username and friend_username are required"}), 400

    if username == friend_username:
        return jsonify({"error": "cannot create friendship with yourself"}), 400

    users_collection = db["users"]
    friendships_collection = db["friendships"]

    requester = users_collection.find_one({"username": username})
    target = users_collection.find_one({"username": friend_username})

    if not requester or not target:
        return jsonify({"error": "both users must exist"}), 404

    user1_id, user2_id = ordered_pair_ids(requester["_id"], target["_id"])

    try:
        result = friendships_collection.update_one(
            {"user1_id": user1_id, "user2_id": user2_id},
            {
                "$setOnInsert": {
                    "user1_id": user1_id,
                    "user2_id": user2_id,
                    "status": "accepted",
                    "requested_by": requester["_id"],
                    "requested_at": datetime.now(timezone.utc),
                    "accepted_at": None,
                }
            },
            upsert=True,
        )
    except DuplicateKeyError:
        return jsonify({"error": "friendship already exists"}), 409

    if result.upserted_id is None:
        return jsonify({"error": "friendship already exists"}), 409

    return (
        jsonify(
            {
                "id": str(result.upserted_id),
                "username": username,
                "friend_username": friend_username,
                "status": "pending",
            }
        ),
        201,
    )


@app.route("/api/friendships", methods=["GET"])
def list_friendships():
    username = request.args.get("username", "").strip()

    if not username:
        return jsonify({"error": "username query param is required"}), 400

    users_collection = db["users"]
    friendships_collection = db["friendships"]

    user = users_collection.find_one({"username": username})
    if not user:
        return jsonify({"error": "user not found"}), 404

    friendships = friendships_collection.find(
        {"$or": [{"user1_id": user["_id"]}, {"user2_id": user["_id"]}]}
    )

    items = []
    for friendship in friendships:
        if friendship["user1_id"] == user["_id"]:
            friend_id = friendship["user2_id"]
        else:
            friend_id = friendship["user1_id"]

        friend_user = users_collection.find_one({"_id": friend_id})
        items.append(
            {
                "friend_username": friend_user["username"] if friend_user else None,
                "status": friendship.get("status", "pending"),
            }
        )

    return jsonify({"username": username, "friendships": items}), 200


@app.route("/api/expenses", methods=["POST"])
def create_expense():
    data = get_json_object()
    if data is None:
        return jsonify({"error": "request body must be a JSON object"}), 400

    payer_username = data.get("payer_username", "").strip()
    debtor_username = data.get("debtor_username", "").strip()
    total_amount_raw = data.get("total_amount")
    amount_owed_raw = data.get("amount_owed")
    description = data.get("description", "").strip()
    category = data.get("category", "").strip() or "general"
    date_raw = data.get("date", "")

    if not payer_username or not debtor_username:
        return jsonify({"error": "payer_username and debtor_username are required"}), 400
    if payer_username == debtor_username:
        return jsonify({"error": "payer and debtor must be different users"}), 400
    if not description:
        return jsonify({"error": "description is required"}), 400

    try:
        total_amount = float(total_amount_raw)
        amount_owed = float(amount_owed_raw)
    except (TypeError, ValueError):
        return jsonify({"error": "amount fields must be numeric"}), 400

    if total_amount <= 0 or amount_owed <= 0:
        return jsonify({"error": "amount fields must be greater than zero"}), 400
    if amount_owed > total_amount:
        return jsonify({"error": "amount_owed cannot exceed total_amount"}), 400

    try:
        expense_date = parse_iso_datetime(date_raw)
    except ValueError:
        return jsonify({"error": "date must be ISO-8601 format"}), 400

    users_collection = db["users"]
    expenses_collection = db["expenses"]

    payer = users_collection.find_one({"username": payer_username})
    debtor = users_collection.find_one({"username": debtor_username})
    if not payer or not debtor:
        return jsonify({"error": "both users must exist"}), 404

    expense = {
        "payer_id": payer["_id"],
        "debtor_id": debtor["_id"],
        "total_amount": total_amount,
        "amount_owed": amount_owed,
        "description": description,
        "category": category,
        "date": expense_date,
        "created_at": datetime.now(timezone.utc),
        "created_by": payer["_id"],
    }
    result = expenses_collection.insert_one(expense)

    return (
        jsonify(
            {
                "id": str(result.inserted_id),
                "payer_username": payer_username,
                "debtor_username": debtor_username,
                "amount_owed": amount_owed,
            }
        ),
        201,
    )


@app.route("/api/expenses", methods=["GET"])
def list_expenses():
    username = request.args.get("username", "").strip()
    if not username:
        return jsonify({"error": "username query param is required"}), 400

    users_collection = db["users"]
    expenses_collection = db["expenses"]

    user = users_collection.find_one({"username": username})
    if not user:
        return jsonify({"error": "user not found"}), 404

    expenses = expenses_collection.find(
        {"$or": [{"payer_id": user["_id"]}, {"debtor_id": user["_id"]}]}
    )

    items = []
    for expense in expenses:
        payer = users_collection.find_one({"_id": expense["payer_id"]})
        debtor = users_collection.find_one({"_id": expense["debtor_id"]})
        items.append(
            {
                "id": str(expense.get("_id")),
                "payer_username": payer["username"] if payer else None,
                "debtor_username": debtor["username"] if debtor else None,
                "description": expense.get("description"),
                "amount_owed": expense.get("amount_owed"),
                "total_amount": expense.get("total_amount"),
                "category": expense.get("category"),
            }
        )

    return jsonify({"username": username, "expenses": items}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
