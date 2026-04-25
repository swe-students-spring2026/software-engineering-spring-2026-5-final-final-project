from app.ai.tools import get_courses, generate_schedule, TOOL_HANDLERS, GEMINI_TOOL


class TestGetCourses:
    def test_returns_all_courses_with_no_filters(self):
        result = get_courses()
        assert "courses" in result
        assert len(result["courses"]) == 5

    def test_filters_by_department(self):
        result = get_courses(department="CS")
        courses = result["courses"]
        assert all(c["department"] == "CS" for c in courses)
        assert len(courses) == 4

    def test_filters_by_department_case_insensitive(self):
        result = get_courses(department="cs")
        assert len(result["courses"]) == 4

    def test_filters_by_level(self):
        result = get_courses(level=4000)
        courses = result["courses"]
        assert all(c["level"] == 4000 for c in courses)
        assert len(courses) == 2

    def test_filters_by_department_and_level(self):
        result = get_courses(department="CS", level=3000)
        courses = result["courses"]
        assert len(courses) == 2
        assert all(c["department"] == "CS" and c["level"] == 3000 for c in courses)

    def test_unknown_department_returns_empty(self):
        result = get_courses(department="ZZZZ")
        assert result["courses"] == []

    def test_course_schema(self):
        result = get_courses(department="MATH")
        course = result["courses"][0]
        assert "id" in course
        assert "name" in course
        assert "credits" in course


class TestGenerateSchedule:
    def test_returns_schedule_with_correct_courses(self):
        result = generate_schedule(["CS-3001", "CS-4001"])
        assert result["semester"] == "Fall 2025"
        assert len(result["schedule"]) == 2
        ids = [s["course_id"] for s in result["schedule"]]
        assert "CS-3001" in ids
        assert "CS-4001" in ids

    def test_custom_semester(self):
        result = generate_schedule(["CS-3001"], semester="Spring 2026")
        assert result["semester"] == "Spring 2026"

    def test_schedule_entries_have_required_fields(self):
        result = generate_schedule(["CS-3001"])
        entry = result["schedule"][0]
        assert "course_id" in entry
        assert "days" in entry
        assert "time" in entry

    def test_empty_course_list(self):
        result = generate_schedule([])
        assert result["schedule"] == []

    def test_days_cycle_for_multiple_courses(self):
        courses = ["A", "B", "C", "D"]
        result = generate_schedule(courses)
        days = [s["days"] for s in result["schedule"]]
        assert days[0] != days[1]  # MWF vs TTh alternation


class TestToolHandlers:
    def test_handlers_registered(self):
        assert "get_courses" in TOOL_HANDLERS
        assert "generate_schedule" in TOOL_HANDLERS

    def test_handlers_are_callable(self):
        assert callable(TOOL_HANDLERS["get_courses"])
        assert callable(TOOL_HANDLERS["generate_schedule"])

    def test_gemini_tool_is_defined(self):
        assert GEMINI_TOOL is not None
