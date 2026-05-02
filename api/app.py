import os
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

client = MongoClient(os.environ["MONGO_URI"])
db = client[os.environ.get("MONGO_DBNAME", "splitring")]


@app.route("/api/users", methods=["POST"])
def create_user():
    data = request.get_json()

    username = (data or {}).get("username", "").strip()
    password = (data or {}).get("password", "").strip()
    email_raw = (data or {}).get("email") or ""
    email = email_raw.strip() or None

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    user = {
        "username": username,
        "password_hash": generate_password_hash(password),
        "email": email,
        "created_at": datetime.now(timezone.utc),
    }

    try:
        result = db["users"].insert_one(user)
    except DuplicateKeyError as e:
        key = "email" if "email" in str(e) else "username"
        return jsonify({"error": f"{key} already taken"}), 409

    return jsonify({"id": str(result.inserted_id), "username": username}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()

    username = (data or {}).get("username", "").strip()
    password = (data or {}).get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    user = db["users"].find_one({"username": username})
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "invalid credentials"}), 401

    return jsonify({"id": str(user["_id"]), "username": user["username"]}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
