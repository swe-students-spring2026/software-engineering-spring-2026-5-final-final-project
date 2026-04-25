from unittest.mock import patch


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
