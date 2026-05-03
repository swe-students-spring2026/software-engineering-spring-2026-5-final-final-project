from flask import Blueprint, request, jsonify, Response

from app.ai.service import chat

chat_bp = Blueprint("chat", __name__)


@chat_bp.post("/chat")
def chat_endpoint() -> tuple[Response, int] | Response:
    data: dict = request.get_json(silent=True) or {}
    message: str = data.get("message", "").strip()
    completed_courses: list[str] = data.get("completed_courses") or []
    major: str = data.get("major", "").strip()
    student_profile: dict = data.get("student_profile") or {}
    history: list = data.get("history") or []

    if not message:
        return jsonify({"error": "message is required"}), 400

    try:
        reply = chat(
            message,
            completed_courses=completed_courses,
            major=major,
            student_profile=student_profile,
            history=history,
        )
        return jsonify({"reply": reply})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
