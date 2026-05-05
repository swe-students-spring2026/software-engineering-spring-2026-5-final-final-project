"""Tests for app.services.transcript_parser.

Covers both:
  - the deterministic regex path (conventional NYU undergraduate format)
  - the Gemini fallback path (unconventional / non-matching formats)
  - the parse_transcript() orchestrator that decides between them
"""
from unittest.mock import MagicMock, patch


class TestRegexPath:
    """The regex parser handles conventional NYU undergraduate transcripts."""

    def test_parses_standard_undergraduate_format(self):
        from app.services import transcript_parser
        text = (
            "Linear Algebra MATH-UA  140-001 4.0 A \n"
            "Intro to Computer Science CSCI-UA  101-002 4.0 A- \n"
            "Microeconomics ECON-UB    2-001 4.0 B+ \n"
        )
        result = transcript_parser._parse_transcript_regex(text)
        assert result["completed"] == ["MATH-UA 140", "CSCI-UA 101", "ECON-UB 2"]
        assert result["current"] == []
        assert result["course_credits"] == {
            "MATH-UA 140": 4,
            "CSCI-UA 101": 4,
            "ECON-UB 2": 4,
        }

    def test_currently_enrolled_marker_goes_to_current(self):
        from app.services import transcript_parser
        text = "Software Engineering CSCI-UA  474-001 4.0 *** \n"
        result = transcript_parser._parse_transcript_regex(text)
        assert result["current"] == ["CSCI-UA 474"]
        assert result["completed"] == []
        assert result["course_credits"] == {"CSCI-UA 474": 4}

    def test_separates_test_credits_section(self):
        from app.services import transcript_parser
        text = (
            "Test Credits Applied Toward Fall 2021\n"
            "ADV_PL Calculus BC 4.0\n"
            "ADV_PL Chemistry 8.0\n"
            "Linear Algebra MATH-UA  140-001 4.0 A \n"
        )
        result = transcript_parser._parse_transcript_regex(text)
        assert result["completed"] == ["MATH-UA 140"]
        assert result["test_credits"] == [
            {"test": "ADV_PL", "component": "Calculus BC", "units": 4},
            {"test": "ADV_PL", "component": "Chemistry", "units": 8},
        ]
        assert result["test_credit_total"] == 12

    def test_excludes_withdrawn_and_incomplete_grades(self):
        from app.services import transcript_parser
        text = (
            "Course One ABCD-UA  100-001 4.0 W \n"
            "Course Two ABCD-UA  101-001 4.0 I \n"
            "Course Three ABCD-UA  102-001 4.0 AU \n"
            "Course Four ABCD-UA  103-001 4.0 A \n"
        )
        result = transcript_parser._parse_transcript_regex(text)
        assert result["completed"] == ["ABCD-UA 103"]
        assert result["current"] == []

    def test_withdraw_then_retake_counts_the_retake(self):
        """A withdrawn first attempt must not block a later valid retake."""
        from app.services import transcript_parser
        text = (
            "Course X ABCD-UA  100-001 4.0 W \n"
            "Course X ABCD-UA  100-002 4.0 A \n"
        )
        result = transcript_parser._parse_transcript_regex(text)
        assert result["completed"] == ["ABCD-UA 100"]
        assert result["course_credits"]["ABCD-UA 100"] == 4

    def test_first_valid_attempt_wins_when_repeated(self):
        from app.services import transcript_parser
        text = (
            "Course One ABCD-UA  100-001 4.0 A \n"
            "Course One Retake ABCD-UA  100-002 4.0 B+ \n"
        )
        result = transcript_parser._parse_transcript_regex(text)
        assert result["completed"] == ["ABCD-UA 100"]

    def test_fractional_credits_preserved_as_float(self):
        from app.services import transcript_parser
        text = "Music Theory MUSC-UA  100-001 1.5 A \n"
        result = transcript_parser._parse_transcript_regex(text)
        assert result["course_credits"]["MUSC-UA 100"] == 1.5

    def test_zero_credit_pass_fail_courses_counted(self):
        from app.services import transcript_parser
        text = "Cohort Leadership MULT-UB    9-016 0.0 P \n"
        result = transcript_parser._parse_transcript_regex(text)
        assert result["completed"] == ["MULT-UB 9"]
        assert result["course_credits"]["MULT-UB 9"] == 0

    def test_transfer_credit_grade_T_counts(self):
        from app.services import transcript_parser
        text = "Transferred Course XFER-UA  50-001 3.0 T \n"
        result = transcript_parser._parse_transcript_regex(text)
        assert result["completed"] == ["XFER-UA 50"]

    def test_empty_input_returns_empty(self):
        from app.services import transcript_parser
        result = transcript_parser._parse_transcript_regex("")
        assert result == {
            "completed": [],
            "current": [],
            "course_credits": {},
            "test_credits": [],
            "test_credit_total": 0,
        }

    def test_no_courses_in_text_returns_empty(self):
        from app.services import transcript_parser
        result = transcript_parser._parse_transcript_regex("This is not a transcript.")
        assert result == {
            "completed": [],
            "current": [],
            "course_credits": {},
            "test_credits": [],
            "test_credit_total": 0,
        }


class TestParseTranscriptOrchestrator:
    """parse_transcript() chooses regex first, AI fallback second."""

    def test_regex_match_skips_ai_fallback(self):
        from app.services import transcript_parser
        text = "Linear Algebra MATH-UA  140-001 4.0 A \n"
        with patch.object(transcript_parser, "_parse_transcript_ai") as mock_ai:
            result = transcript_parser.parse_transcript(text)
        mock_ai.assert_not_called()
        assert "MATH-UA 140" in result["completed"]

    def test_test_credit_only_transcript_skips_ai_fallback(self):
        from app.services import transcript_parser
        text = "Test Credits Applied Toward Fall 2021\nADV_PL Chemistry 8.0\n"
        with patch.object(transcript_parser, "_parse_transcript_ai") as mock_ai:
            result = transcript_parser.parse_transcript(text)
        mock_ai.assert_not_called()
        assert result["test_credit_total"] == 8

    def test_parse_test_credits_extracts_only_test_credit_rows(self):
        from app.services import transcript_parser
        text = (
            "Test Credits Applied Toward Fall 2021\n"
            "ADV_PL Chemistry 8.0\n"
            "CSCI-UA 101-001 4.0 A Intro to Computer Science\n"
            "ADV_PL Calculus BC 4.0\n"
        )
        result = transcript_parser.parse_test_credits(text)
        assert result == {
            "test_credits": [
                {"test": "ADV_PL", "component": "Chemistry", "units": 8},
                {"test": "ADV_PL", "component": "Calculus BC", "units": 4},
            ],
            "test_credit_total": 12,
        }

    def test_unconventional_input_falls_back_to_ai(self):
        """A non-NYU-format transcript triggers the AI fallback."""
        from app.services import transcript_parser
        ai_payload = {"completed": ["FAKE-UA 1"], "current": [], "course_credits": {"FAKE-UA 1": 3}}
        with patch.object(transcript_parser, "_parse_transcript_ai", return_value=ai_payload) as mock_ai:
            result = transcript_parser.parse_transcript("an unusual transcript layout")
        mock_ai.assert_called_once()
        assert result == ai_payload


class TestAIFallback:
    """Tests for the Gemini-backed fallback path."""

    def test_returns_parsed_json_from_model_response(self):
        from app.services import transcript_parser
        mock_resp = MagicMock()
        mock_resp.text = (
            '{"completed": ["CSCI-UA 101", "MATH-UA 123"], "current": [], '
            '"course_credits": {"CSCI-UA 101": 4, "MATH-UA 123": 4}}'
        )
        with patch.object(transcript_parser.client.models, "generate_content", return_value=mock_resp):
            result = transcript_parser._parse_transcript_ai("anything")
        assert "CSCI-UA 101" in result["completed"]
        assert "MATH-UA 123" in result["completed"]
        assert result["course_credits"]["CSCI-UA 101"] == 4
        assert result["test_credits"] == []
        assert result["test_credit_total"] == 0

    def test_returns_empty_on_unparseable_response(self):
        from app.services import transcript_parser
        mock_resp = MagicMock()
        mock_resp.text = "Sorry, I cannot parse this."
        with patch.object(transcript_parser.client.models, "generate_content", return_value=mock_resp):
            result = transcript_parser._parse_transcript_ai("gibberish")
        assert result == {
            "completed": [],
            "current": [],
            "course_credits": {},
            "test_credits": [],
            "test_credit_total": 0,
        }

    def test_returns_empty_on_empty_response(self):
        from app.services import transcript_parser
        mock_resp = MagicMock()
        mock_resp.text = ""
        with patch.object(transcript_parser.client.models, "generate_content", return_value=mock_resp):
            result = transcript_parser._parse_transcript_ai("")
        assert result == {
            "completed": [],
            "current": [],
            "course_credits": {},
            "test_credits": [],
            "test_credit_total": 0,
        }
