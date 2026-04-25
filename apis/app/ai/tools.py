"""
Tool definitions and handler functions that query MongoDB.

GEMINI_TOOL contains all function declarations.
TOOL_HANDLERS maps each tool name to its handler.
Call init_tools(db) once at startup to wire in the database.
"""

from typing import Any

from google.genai import types

_db = None


def init_tools(db) -> None:
    global _db
    _db = db


# ── Gemini tool schema ────────────────────────────────────────────────────────

GEMINI_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="search_courses",
            description=(
                "Search the NYU course catalog for courses matching a keyword, "
                "department/subject code, or component type. Returns matching "
                "courses with titles, descriptions, sections, and enrollment status."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(
                        type=types.Type.STRING,
                        description="Keyword to match against course title, code, or description.",
                    ),
                    "department": types.Schema(
                        type=types.Type.STRING,
                        description="Subject/department code to filter by, e.g. 'CSCI' or 'MATH'.",
                    ),
                    "term": types.Schema(
                        type=types.Type.STRING,
                        description="Term code to filter by, e.g. '1268' for Fall 2026.",
                    ),
                    "component": types.Schema(
                        type=types.Type.STRING,
                        description="Component type: Lecture, Recitation, Seminar, or Lab.",
                    ),
                    "limit": types.Schema(
                        type=types.Type.INTEGER,
                        description="Maximum number of results to return (default 20).",
                    ),
                },
            ),
        ),
        types.FunctionDeclaration(
            name="get_course_sections",
            description=(
                "Get all available sections for a course by its code or name, "
                "including meeting times, instructor, location, and enrollment status. "
                "Accepts a course code like 'CSCI-UA 101' OR a course name/title "
                "like 'Data Structures' or 'Calculus'."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "course_code": types.Schema(
                        type=types.Type.STRING,
                        description=(
                            "Course code (e.g. 'CSCI-UA 101') OR course name/title "
                            "(e.g. 'Data Structures', 'Linear Algebra')."
                        ),
                    ),
                    "term": types.Schema(
                        type=types.Type.STRING,
                        description=(
                            "Term code to filter by, e.g. '1268' for Fall 2026."
                        ),
                    ),
                },
                required=["course_code"],
            ),
        ),
        types.FunctionDeclaration(
            name="list_programs",
            description="List all available NYU undergraduate programs and majors.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={},
            ),
        ),
        types.FunctionDeclaration(
            name="get_program_requirements",
            description=(
                "Get the full degree requirements for a specific NYU program, "
                "identified by its URL from list_programs."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "url": types.Schema(
                        type=types.Type.STRING,
                        description="The program URL returned by list_programs.",
                    ),
                },
                required=["url"],
            ),
        ),
    ]
)


# ── Handler functions ─────────────────────────────────────────────────────────

def search_courses(
    query: str = "",
    department: str = "",
    term: str = "",
    component: str = "",
    limit: int = 20,
) -> dict[str, Any]:
    """Search course catalog in MongoDB."""
    if _db is None:
        return {"error": "Database not initialized"}

    conditions: list[dict] = []

    if term:
        conditions.append({"term.code": term})
    if component:
        conditions.append({"component": {"$regex": component, "$options": "i"}})
    if department:
        conditions.append({"$or": [
            {"subject_code": {"$regex": department, "$options": "i"}},
            {"code": {"$regex": department, "$options": "i"}},
        ]})
    if query:
        conditions.append({"$or": [
            {"title": {"$regex": query, "$options": "i"}},
            {"code": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}},
        ]})

    if len(conditions) > 1:
        filter_query: dict = {"$and": conditions}
    elif conditions:
        filter_query = conditions[0]
    else:
        filter_query = {}

    courses = list(_db.classes.find(
        filter_query,
        {
            "_id": 0, "code": 1, "title": 1, "description": 1, "credits": 1,
            "school": 1, "subject_code": 1, "component": 1, "section": 1,
            "crn": 1, "instructor": 1, "meets_human": 1, "status": 1,
            "term": 1, "prerequisites": 1,
        },
    ).limit(limit))

    return {"courses": courses, "count": len(courses)}


def get_course_sections(course_code: str, term: str = "") -> dict[str, Any]:
    """Get all sections matching a course code or title from MongoDB."""
    if _db is None:
        return {"error": "Database not initialized"}

    or_clause = {"$or": [
        {"code": {"$regex": course_code, "$options": "i"}},
        {"title": {"$regex": course_code, "$options": "i"}},
    ]}
    if term:
        query: dict = {"$and": [or_clause, {"term.code": term}]}
    else:
        query = or_clause

    sections = list(_db.classes.find(
        query,
        {
            "_id": 0, "code": 1, "title": 1, "section": 1, "crn": 1,
            "instructor": 1, "meets_human": 1, "meeting_times": 1,
            "status": 1, "component": 1, "instructional_method": 1,
            "campus_location": 1, "credits": 1,
        },
    ))

    return {"course_code": course_code, "sections": sections, "count": len(sections)}


def list_programs() -> dict[str, Any]:
    """List all undergraduate programs from MongoDB."""
    if _db is None:
        return {"error": "Database not initialized"}

    programs = list(_db.program_requirements.find(
        {},
        {"_id": 0, "title": 1, "url": 1, "school": 1, "award": 1},
    ).sort("title", 1).limit(200))

    return {"programs": programs, "count": len(programs)}


def get_program_requirements(url: str) -> dict[str, Any]:
    """Fetch full degree requirements for a program by URL."""
    if _db is None:
        return {"error": "Database not initialized"}

    program = _db.program_requirements.find_one({"url": url}, {"_id": 0})
    if not program:
        return {"error": f"Program not found for URL: {url}"}
    return program


# ── Dispatch table ────────────────────────────────────────────────────────────

TOOL_HANDLERS: dict[str, Any] = {
    "search_courses": search_courses,
    "get_course_sections": get_course_sections,
    "list_programs": list_programs,
    "get_program_requirements": get_program_requirements,
}
