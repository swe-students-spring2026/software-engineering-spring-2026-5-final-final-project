import pytest
from unittest.mock import patch

from app.routes.chat import _reset_rate_limit_for_testing


@pytest.fixture(autouse=True)
def _clear_rate_buckets():
    """Reset in-memory rate-limit state before every test."""
    _reset_rate_limit_for_testing()
    yield
    _reset_rate_limit_for_testing()


class TestChatRoute:
    def test_chat_returns_reply(self, client):
        with patch("app.routes.chat.chat", return_value="Here are some courses."):
            res = client.post("/chat", json={"message": "what courses are there?"})
        assert res.status_code == 200
        assert res.get_json()["reply"] == "Here are some courses."

    def test_chat_missing_message_returns_400(self, client):
        res = client.post("/chat", json={})
        assert res.status_code == 400
        assert "error" in res.get_json()

    def test_chat_empty_message_returns_400(self, client):
        res = client.post("/chat", json={"message": "   "})
        assert res.status_code == 400

    def test_chat_no_body_returns_400(self, client):
        res = client.post("/chat", content_type="application/json", data="")
        assert res.status_code == 400

    def test_chat_service_error_returns_500(self, client):
        with patch("app.routes.chat.chat", side_effect=Exception("Gemini error")):
            res = client.post("/chat", json={"message": "hello"})
        assert res.status_code == 500
        assert "error" in res.get_json()

    def test_chat_accepts_complex_message(self, client):
        with patch("app.routes.chat.chat", return_value="Schedule created."):
            res = client.post("/chat", json={"message": "make me a schedule with 3 CS courses"})
        assert res.status_code == 200

    def test_chat_passes_student_profile_to_service(self, client):
        with patch("app.routes.chat.chat", return_value="Profile-aware reply.") as mock_chat:
            res = client.post(
                "/chat",
                json={
                    "message": "recommend courses",
                    "student_profile": {
                        "major": "CS",
                        "completed_courses": ["CSCI-UA 101"],
                        "current_courses": ["CSCI-UA 201"],
                    },
                },
            )
        assert res.status_code == 200
        assert mock_chat.call_args.kwargs["student_profile"]["major"] == "CS"


class TestChatAuth:
    """The /chat endpoint must reject requests without the internal token."""

    def test_missing_token_returns_403(self, flask_app):
        with flask_app.test_client() as c:
            res = c.post("/chat", json={"message": "hello"})
        assert res.status_code == 403
        assert "forbidden" in res.get_json().get("error", "").lower()

    def test_wrong_token_returns_403(self, flask_app):
        with flask_app.test_client() as c:
            c.environ_base["HTTP_X_INTERNAL_API_TOKEN"] = "wrong-token"
            res = c.post("/chat", json={"message": "hello"})
        assert res.status_code == 403

    def test_correct_token_is_accepted(self, client):
        with patch("app.routes.chat.chat", return_value="ok"):
            res = client.post("/chat", json={"message": "hello"})
        assert res.status_code == 200
