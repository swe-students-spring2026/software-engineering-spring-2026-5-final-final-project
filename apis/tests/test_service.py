import app.ai.tools as tools_module
from unittest.mock import MagicMock, patch


class TestExecuteTool:
    def test_unknown_tool_returns_error(self):
        from app.ai.service import _execute_tool
        result = _execute_tool("nonexistent_tool", {})
        assert "error" in result
        assert "nonexistent_tool" in result["error"]

    def test_known_tool_search_courses(self):
        db = MagicMock()
        db.classes.find.return_value.limit.return_value = []
        tools_module._db = db
        from app.ai.service import _execute_tool
        result = _execute_tool("search_courses", {"department": "CSCI"})
        assert "courses" in result

    def test_known_tool_get_course_sections(self):
        db = MagicMock()
        db.classes.find.return_value = []
        tools_module._db = db
        from app.ai.service import _execute_tool
        result = _execute_tool("get_course_sections", {"course_code": "CSCI-UA 101"})
        assert "sections" in result

    def test_bad_args_returns_error(self):
        db = MagicMock()
        db.classes.find.return_value = []
        tools_module._db = db
        from app.ai.service import _execute_tool
        result = _execute_tool("get_course_sections", {"bad_arg": 999})
        assert "error" in result


class TestChat:
    def _make_response(self, text: str, function_calls=None):
        response = MagicMock()
        response.function_calls = function_calls or []
        response.text = text
        return response

    def test_chat_returns_text_with_no_tool_calls(self):
        from app.ai import service
        mock_response = self._make_response("Here are some courses.")
        with patch.object(service._client.models, "generate_content", return_value=mock_response):
            result = service.chat("what courses are available?")
        assert result == "Here are some courses."

    def test_chat_returns_empty_string_on_no_text(self):
        from app.ai import service
        mock_response = MagicMock()
        mock_response.function_calls = []
        mock_response.text = ""
        with patch.object(service._client.models, "generate_content", return_value=mock_response):
            result = service.chat("hello")
        assert result == ""

    def test_chat_executes_tool_call_and_continues(self):
        from app.ai import service

        fc = MagicMock()
        fc.name = "search_courses"
        fc.args = {"department": "CSCI"}

        first_response = MagicMock()
        first_response.function_calls = [fc]
        first_response.candidates = [MagicMock()]
        first_response.candidates[0].content = MagicMock()

        second_response = MagicMock()
        second_response.function_calls = []
        second_response.text = "I found CS courses for you."

        with patch.object(
            service._client.models, "generate_content",
            side_effect=[first_response, second_response]
        ):
            result = service.chat("show me CS courses")

        assert result == "I found CS courses for you."

    def test_chat_includes_context_in_message(self):
        from app.ai import service
        service.types.Part.from_text.reset_mock()
        mock_response = self._make_response("Here are your recommendations.")
        with patch.object(service._client.models, "generate_content", return_value=mock_response):
            service.chat(
                "recommend courses",
                completed_courses=["CSCI-UA 101"],
                major="Computer Science",
            )
        # types is stubbed in CI; inspect the text passed to Part.from_text directly
        last_call = service.types.Part.from_text.call_args
        text = last_call.kwargs.get("text") or last_call.args[0]
        assert "Computer Science" in text
        assert "CSCI-UA 101" in text

    def test_chat_no_context_sends_message_as_is(self):
        from app.ai import service
        service.types.Part.from_text.reset_mock()
        mock_response = self._make_response("Reply.")
        with patch.object(service._client.models, "generate_content", return_value=mock_response):
            service.chat("just a question")
        from_text_calls = service.types.Part.from_text.call_args_list
        text = from_text_calls[0].kwargs.get("text") or from_text_calls[0].args[0]
        assert text == "just a question"


class TestMongoEncoder:
    def test_encodes_datetime(self):
        import json
        from datetime import datetime
        from app.ai.service import _MongoEncoder
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = json.dumps({"ts": dt}, cls=_MongoEncoder)
        assert "2024-01-15" in result

    def test_encodes_unknown_as_str(self):
        import json
        from app.ai.service import _MongoEncoder

        class _Fake:
            def __str__(self):
                return "fake-id-value"

        result = json.dumps({"id": _Fake()}, cls=_MongoEncoder)
        assert "fake-id-value" in result


class TestParseTranscript:
    def test_returns_list_of_course_codes(self):
        from app.ai import service
        mock_resp = MagicMock()
        mock_resp.text = '["CSCI-UA 101", "MATH-UA 123"]'
        with patch.object(service._client.models, "generate_content", return_value=mock_resp):
            result = service.parse_transcript("sample transcript text")
        assert "CSCI-UA 101" in result
        assert "MATH-UA 123" in result

    def test_returns_empty_list_on_bad_response(self):
        from app.ai import service
        mock_resp = MagicMock()
        mock_resp.text = "Sorry, I cannot parse this."
        with patch.object(service._client.models, "generate_content", return_value=mock_resp):
            result = service.parse_transcript("gibberish")
        assert result == []

    def test_returns_empty_list_on_empty_response(self):
        from app.ai import service
        mock_resp = MagicMock()
        mock_resp.text = ""
        with patch.object(service._client.models, "generate_content", return_value=mock_resp):
            result = service.parse_transcript("")
        assert result == []
