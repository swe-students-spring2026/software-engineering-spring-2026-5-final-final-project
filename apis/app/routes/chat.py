from flask import Blueprint, request, jsonify, Response

from app.ai.service import chat

chat_bp = Blueprint("chat", __name__)


@chat_bp.post("/chat")
def chat_endpoint() -> tuple[Response, int] | Response:
    data: dict = request.get_json(silent=True) or {}
    message: str = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "message is required"}), 400

    try:
        reply = chat(message)
        return jsonify({"reply": reply})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
