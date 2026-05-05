import os
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

client = MongoClient(os.environ["MONGO_URI"])
db = client[os.environ.get("MONGO_DBNAME", "splitring")]


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
                    "status": "pending",
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
