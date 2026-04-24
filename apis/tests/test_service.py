import json
from unittest.mock import MagicMock, patch

import pytest


class TestExecuteTool:
    def test_unknown_tool_returns_error(self):
        from app.ai.service import _execute_tool
        result = _execute_tool("nonexistent_tool", {})
        assert "error" in result
        assert "nonexistent_tool" in result["error"]

    def test_known_tool_get_courses(self):
        from app.ai.service import _execute_tool
        result = _execute_tool("get_courses", {"department": "CS"})
        assert "courses" in result

    def test_known_tool_generate_schedule(self):
        from app.ai.service import _execute_tool
        result = _execute_tool("generate_schedule", {"courses": ["CS-3001"]})
        assert "schedule" in result

    def test_bad_args_returns_error(self):
        from app.ai.service import _execute_tool
        result = _execute_tool("generate_schedule", {"bad_arg": 999})
        assert "error" in result


class TestChat:
    def _make_response(self, text: str, function_calls=None):
        response = MagicMock()
        response.function_calls = function_calls or []
        msg = MagicMock()
        msg.type = "message"
        part = MagicMock()
        part.type = "output_text"
        part.text = text
        msg.content = [part]
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

        # First response has a function call
        fc = MagicMock()
        fc.name = "get_courses"
        fc.args = {"department": "CS"}

        first_response = MagicMock()
        first_response.function_calls = [fc]
        first_response.candidates = [MagicMock()]
        first_response.candidates[0].content = MagicMock()

        # Second response is the final text
        second_response = MagicMock()
        second_response.function_calls = []
        second_response.text = "I found CS courses for you."

        with patch.object(
            service._client.models, "generate_content",
            side_effect=[first_response, second_response]
        ):
            result = service.chat("show me CS courses")

        assert result == "I found CS courses for you."
