import app.ai.tools as tools_module
import pytest
from unittest.mock import MagicMock
from app.ai.tools import (
    search_courses,
    get_course_sections,
    get_professor_profile,
    list_programs,
    get_program_requirements,
    TOOL_HANDLERS,
    GEMINI_TOOL,
)


@pytest.fixture(autouse=True)
def mock_db():
    """Inject a mock database before each test and tear it down after."""
    db = MagicMock()
    tools_module._db = db
    yield db
    tools_module._db = None


class TestSearchCourses:
    def test_returns_courses_from_db(self, mock_db):
        mock_db.classes.find.return_value.limit.return_value = [
            {"code": "CSCI-UA 101", "title": "Intro to CS", "credits": 4},
        ]
        result = search_courses()
        assert "courses" in result
        assert result["count"] == 1

    def test_returns_top_level_topic(self, mock_db):
        mock_db.classes.find.return_value.limit.return_value = [
            {
                "code": "CORE-UA 400",
                "title": "Texts and Ideas",
                "topic": "The Black Radical Tradition",
            },
        ]
        result = search_courses()
        assert result["courses"][0]["topic"] == "The Black Radical Tradition"

    def test_slim_search_projection_includes_topic(self, mock_db):
        mock_db.classes.find.return_value.limit.return_value = []
        search_courses()
        projection = mock_db.classes.find.call_args[0][1]
        assert projection["topic"] == 1

    def test_no_db_returns_error(self):
        tools_module._db = None
        result = search_courses(query="algorithms")
        assert "error" in result

    def test_with_query_builds_regex_filter(self, mock_db):
        mock_db.classes.find.return_value.limit.return_value = []
        search_courses(query="machine learning")
        filter_arg = mock_db.classes.find.call_args[0][0]
        assert "machine learning" in str(filter_arg)

    def test_with_term_filter(self, mock_db):
        mock_db.classes.find.return_value.limit.return_value = []
        search_courses(term="1268")
        filter_arg = mock_db.classes.find.call_args[0][0]
        assert "1268" in str(filter_arg)

    def test_with_department_filter(self, mock_db):
        mock_db.classes.find.return_value.limit.return_value = []
        search_courses(department="CSCI")
        filter_arg = mock_db.classes.find.call_args[0][0]
        assert "CSCI" in str(filter_arg)

    def test_empty_db_returns_empty_list(self, mock_db):
        mock_db.classes.find.return_value.limit.return_value = []
        result = search_courses()
        assert result["courses"] == []
        assert result["count"] == 0

    def test_multiple_filters_use_and(self, mock_db):
        mock_db.classes.find.return_value.limit.return_value = []
        search_courses(query="algorithms", term="1268")
        filter_arg = mock_db.classes.find.call_args[0][0]
        assert "$and" in filter_arg


class TestGetCourseSections:
    def test_returns_sections(self, mock_db):
        mock_db.classes.find.return_value.limit.return_value = [
            {"code": "CSCI-UA 101", "section": "001", "crn": "12345"},
        ]
        result = get_course_sections("CSCI-UA 101")
        assert "sections" in result
        assert result["count"] == 1
        assert result["course_code"] == "CSCI-UA 101"

    def test_no_db_returns_error(self):
        tools_module._db = None
        result = get_course_sections("CSCI-UA 101")
        assert "error" in result

    def test_with_term_filter(self, mock_db):
        mock_db.classes.find.return_value.limit.return_value = []
        get_course_sections("CSCI-UA 101", term="1268")
        filter_arg = mock_db.classes.find.call_args[0][0]
        assert "1268" in str(filter_arg)

    def test_matches_topic(self, mock_db):
        mock_db.classes.find.return_value.limit.return_value = []
        get_course_sections("Of Monsters and Medicine")
        filter_arg = mock_db.classes.find.call_args[0][0]
        assert any("topic" in condition for condition in filter_arg["$or"])

    def test_empty_sections_returns_zero_count(self, mock_db):
        mock_db.classes.find.return_value.limit.return_value = []
        result = get_course_sections("CSCI-UA 999")
        assert result["sections"] == []
        assert result["count"] == 0


class TestGetProfessorProfile:
    def test_returns_professor_profile(self, mock_db):
        mock_db.classes.find.return_value = [
            {"instructor": "Joanna Klukowska", "code": "CSCI-UA 102", "section": "001"}
        ]
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.ai.tools.build_professor_profile", lambda db, name, term="": {
                "name": "Joanna Klukowska",
                "courses": [{"code": "CSCI-UA 102"}],
                "course_count": 1,
            })
            result = get_professor_profile("Joanna Klukowska")
        assert result["name"] == "Joanna Klukowska"

    def test_not_found_returns_error(self, mock_db):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.ai.tools.build_professor_profile", lambda db, name, term="": None)
            result = get_professor_profile("Nobody")
        assert "error" in result


class TestListPrograms:
    def test_returns_programs(self, mock_db):
        mock_db.program_requirements.find.return_value\
            .sort.return_value\
            .limit.return_value = [
            {"title": "Computer Science BS", "url": "/cs", "school": "CAS"},
        ]
        result = list_programs()
        assert "programs" in result
        assert result["count"] == 1

    def test_no_db_returns_error(self):
        tools_module._db = None
        result = list_programs()
        assert "error" in result

    def test_empty_programs_returns_zero_count(self, mock_db):
        mock_db.program_requirements.find.return_value\
            .sort.return_value\
            .limit.return_value = []
        result = list_programs()
        assert result["programs"] == []
        assert result["count"] == 0


class TestGetProgramRequirements:
    def test_returns_program(self, mock_db):
        mock_db.program_requirements.find_one.return_value = {
            "title": "CS BS", "url": "/cs", "requirements": [],
        }
        result = get_program_requirements("/cs")
        assert "title" in result

    def test_not_found_returns_error(self, mock_db):
        mock_db.program_requirements.find_one.return_value = None
        result = get_program_requirements("/nonexistent")
        assert "error" in result

    def test_no_db_returns_error(self):
        tools_module._db = None
        result = get_program_requirements("/cs")
        assert "error" in result


class TestToolHandlers:
    def test_all_handlers_registered(self):
        assert "search_courses" in TOOL_HANDLERS
        assert "get_course_sections" in TOOL_HANDLERS
        assert "list_programs" in TOOL_HANDLERS
        assert "get_program_requirements" in TOOL_HANDLERS
        assert "get_professor_profile" in TOOL_HANDLERS

    def test_handlers_are_callable(self):
        for handler in TOOL_HANDLERS.values():
            assert callable(handler)

    def test_gemini_tool_is_defined(self):
        assert GEMINI_TOOL is not None

    def test_handlers_cover_expected_tools(self):
        expected = {
            "search_courses", "get_course_sections",
            "list_programs", "get_program_requirements", "get_professor_profile",
        }
        assert set(TOOL_HANDLERS.keys()) == expected
