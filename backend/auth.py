"""Authentication endpoints — register and login."""

import datetime

import bcrypt
import jwt
from flask import Blueprint, jsonify, request

from backend.config import JWT_SECRET
from backend.db import get_users_collection

auth_bp = Blueprint("auth", __name__)

_REQUIRED = ["username", "password"]


def _make_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be JSON"}), 400

    for field in _REQUIRED:
        if not data.get(field):
            return jsonify({"error": f"Missing required field: {field}"}), 400

    users = get_users_collection()
    if users.find_one({"username": data["username"]}):
        return jsonify({"error": "Username already exists"}), 409

    hashed = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt())
    result = users.insert_one(
        {
            "username": data["username"],
            "password": hashed,
            "email": data.get("email", ""),
            "created_at": datetime.datetime.utcnow().isoformat(),
        }
    )
    return jsonify({"message": "User registered successfully", "user_id": str(result.inserted_id)}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be JSON"}), 400

    for field in _REQUIRED:
        if not data.get(field):
            return jsonify({"error": f"Missing required field: {field}"}), 400

    users = get_users_collection()
    user = users.find_one({"username": data["username"]})
    if not user or not bcrypt.checkpw(data["password"].encode(), user["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = _make_token(str(user["_id"]))
    return jsonify({"token": token, "user_id": str(user["_id"])}), 200
