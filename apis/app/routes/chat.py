"""Chat blueprint - POST /chat

Security
--------
* **Internal-token guard**: requires the ``X-Internal-API-Token`` header to
  match the ``API_INTERNAL_TOKEN`` env var.  This is the same mechanism used
  by every other protected endpoint in ``main.py`` and ensures the backend
  cannot be hit directly from the public internet.

* **Per-IP rate limit**: sliding-window counter, no extra dependencies.
  Default: 20 requests per 60-second window per remote IP.  Callers that
  exceed the limit receive HTTP 429 until the window rolls forward.
"""

from __future__ import annotations

import os
import threading
import time
from collections import deque

from flask import Blueprint, request, jsonify, Response

from app.ai.service import chat
from app.config.settings import GEMINI_MODEL_CHOICES

chat_bp = Blueprint("chat", __name__)

# ---------------------------------------------------------------------------
# Internal-token guard
# ---------------------------------------------------------------------------

@chat_bp.before_request
def _check_internal_token() -> tuple[Response, int] | None:
    """Reject requests that don't carry the shared backend secret."""
    token = os.environ.get("API_INTERNAL_TOKEN", "")
    if not token:
        return jsonify({"error": "API_INTERNAL_TOKEN is not configured"}), 503
    if request.headers.get("X-Internal-API-Token") != token:
        return jsonify({"error": "forbidden"}), 403
    return None


# ---------------------------------------------------------------------------
# Per-IP sliding-window rate limiter
# ---------------------------------------------------------------------------

_RATE_LIMIT_REQUESTS: int = 20   # max requests …
_RATE_LIMIT_WINDOW: int   = 60   # … per this many seconds

_rate_lock: threading.Lock           = threading.Lock()
_rate_buckets: dict[str, deque[float]] = {}  # IP → request timestamps


def _is_rate_limited(ip: str) -> bool:
    """Return True if *ip* has exceeded the allowed request rate."""
    now    = time.monotonic()
    cutoff = now - _RATE_LIMIT_WINDOW
    with _rate_lock:
        bucket = _rate_buckets.setdefault(ip, deque())
        # Evict timestamps that have fallen outside the current window
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= _RATE_LIMIT_REQUESTS:
            return True
        bucket.append(now)
        return False


def _reset_rate_limit_for_testing() -> None:
    """Clear all rate-limit buckets.  For use in tests only."""
    with _rate_lock:
        _rate_buckets.clear()


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@chat_bp.post("/chat")
def chat_endpoint() -> tuple[Response, int] | Response:
    ip = request.remote_addr or "unknown"
    if _is_rate_limited(ip):
        return (
            jsonify({"error": "Too many requests – please wait a moment before trying again."}),
            429,
        )

    data: dict = request.get_json(silent=True) or {}
    message: str = data.get("message", "").strip()
    completed_courses: list[str] = data.get("completed_courses") or []
    major: str = data.get("major", "").strip()
    student_profile: dict = data.get("student_profile") or {}
    history: list = data.get("history") or []
    # "fast" / "balanced" / "smart" — anything else falls back to default.
    speed: str = str(data.get("speed", "")).strip().lower()
    model = GEMINI_MODEL_CHOICES.get(speed)

    if not message:
        return jsonify({"error": "message is required"}), 400

    try:
        reply = chat(
            message,
            completed_courses=completed_courses,
            major=major,
            student_profile=student_profile,
            history=history,
            model=model,
        )
        return jsonify({"reply": reply})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
