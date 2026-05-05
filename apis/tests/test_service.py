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
        db.classes.find.return_value.limit.return_value = []
        tools_module._db = db
        from app.ai.service import _execute_tool
        result = _execute_tool("get_course_sections", {"course_code": "CSCI-UA 101"})
        assert "sections" in result

    def test_known_tool_get_professor_profile(self):
        db = MagicMock()
        db.classes.find.return_value = []
        tools_module._db = db
        from app.ai.service import _execute_tool
        with patch("app.ai.tools.build_professor_profile", return_value={"name": "Joanna Klukowska", "courses": []}):
            result = _execute_tool("get_professor_profile", {"name": "Joanna Klukowska"})
        assert result["name"] == "Joanna Klukowska"

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
        with patch.object(service.client.models, "generate_content", return_value=mock_response):
            result = service.chat("what courses are available?")
        assert result == "Here are some courses."

    def test_chat_returns_empty_string_on_no_text(self):
        from app.ai import service
        mock_response = MagicMock()
        mock_response.function_calls = []
        mock_response.text = ""
        with patch.object(service.client.models, "generate_content", return_value=mock_response):
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
            service.client.models, "generate_content",
            side_effect=[first_response, second_response]
        ):
            result = service.chat("show me CS courses")

        assert result == "I found CS courses for you."

    def test_chat_includes_context_in_message(self):
        from app.ai import service
        service.types.Part.from_text.reset_mock()
        mock_response = self._make_response("Here are your recommendations.")
        with patch.object(service.client.models, "generate_content", return_value=mock_response):
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

    def test_chat_includes_profile_and_transcript_fields_in_message(self):
        from app.ai import service
        service.types.Part.from_text.reset_mock()
        mock_response = self._make_response("Here are your recommendations.")
        with patch.object(service.client.models, "generate_content", return_value=mock_response):
            service.chat(
                "recommend courses",
                student_profile={
                    "name": "Test User",
                    "school": "CAS",
                    "major": "Computer Science",
                    "minor": "Math",
                    "graduation_year": "2026",
                    "completed_courses": ["CSCI-UA 101"],
                    "current_courses": ["CSCI-UA 201"],
                },
            )
        last_call = service.types.Part.from_text.call_args
        text = last_call.kwargs.get("text") or last_call.args[0]
        assert "Test User" in text
        assert "CAS" in text
        assert "Math" in text
        assert "2026" in text
        assert "CSCI-UA 201" in text

    def test_chat_no_context_sends_message_as_is(self):
        from app.ai import service
        service.types.Part.from_text.reset_mock()
        mock_response = self._make_response("Reply.")
        with patch.object(service.client.models, "generate_content", return_value=mock_response):
            service.chat("just a question")
        from_text_calls = service.types.Part.from_text.call_args_list
        text = from_text_calls[0].kwargs.get("text") or from_text_calls[0].args[0]
        assert "just a question" in text
        assert "SYSTEM NOTE" in text


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


class TestValidateAddCoursesBlock:
    def test_no_block_passthrough(self):
        from app.ai.service import _validate_add_courses_block
        reply = "Just some text, no block here."
        assert _validate_add_courses_block(reply) == reply

    def test_all_valid_kept(self, monkeypatch):
        from app.ai import service
        monkeypatch.setattr(
            service, "verify_section_crns",
            lambda pairs: {("CSCI-UA 102", "12345"), ("MATH-UA 121", "67890")},
        )
        reply = (
            "Schedule:\n"
            "```add-courses\n"
            '[{"code":"CSCI-UA 102","crn":"12345"},'
            '{"code":"MATH-UA 121","crn":"67890"}]\n'
            "```"
        )
        out = service._validate_add_courses_block(reply)
        assert "12345" in out
        assert "67890" in out
        assert "skipped" not in out.lower()

    def test_hallucinated_entry_dropped_with_note(self, monkeypatch):
        from app.ai import service
        # Only the first pair is real; second is hallucinated.
        monkeypatch.setattr(
            service, "verify_section_crns",
            lambda pairs: {("CSCI-UA 102", "12345")},
        )
        reply = (
            "Schedule:\n"
            "```add-courses\n"
            '[{"code":"CSCI-UA 102","crn":"12345"},'
            '{"code":"CORE-UA 750","crn":"9503"}]\n'
            "```"
        )
        out = service._validate_add_courses_block(reply)
        assert "12345" in out
        # Bogus CRN should be gone from the JSON block...
        # (The note line below echoes the dropped CRN — use a clearer marker.)
        assert "CORE-UA 750" in out  # appears in the dropped-note text
        assert "skipped" in out.lower()
        # Only the valid entry remains in the structured block:
        block = out.split("```add-courses")[1].split("```")[0]
        assert "12345" in block
        assert "9503" not in block

    def test_all_invalid_strips_block_and_appends_note(self, monkeypatch):
        from app.ai import service
        monkeypatch.setattr(service, "verify_section_crns", lambda pairs: set())
        reply = (
            "Here you go:\n"
            "```add-courses\n"
            '[{"code":"FAKE-UA 1","crn":"99999"}]\n'
            "```"
        )
        out = service._validate_add_courses_block(reply)
        assert "```add-courses" not in out
        assert "couldn't verify" in out

    def test_malformed_json_strips_block(self, monkeypatch):
        from app.ai import service
        # Should never call verify_section_crns when parsing fails.
        monkeypatch.setattr(service, "verify_section_crns", lambda pairs: set())
        reply = (
            "Oops:\n"
            "```add-courses\n"
            "{not valid json at all]\n"
            "```"
        )
        out = service._validate_add_courses_block(reply)
        assert "```add-courses" not in out

    def test_non_list_json_strips_block(self, monkeypatch):
        from app.ai import service
        monkeypatch.setattr(service, "verify_section_crns", lambda pairs: set())
        reply = (
            "Bad shape:\n"
            "```add-courses\n"
            '{"code":"CSCI-UA 102","crn":"12345"}\n'
            "```"
        )
        out = service._validate_add_courses_block(reply)
        assert "```add-courses" not in out

