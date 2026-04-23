"""
Tool definitions and mock handler functions.

GEMINI_TOOL is a single types.Tool object containing all function declarations.
Each handler in TOOL_HANDLERS is the Python function that runs when the model
invokes the corresponding tool. Replace the mock return values here later
when real data sources are wired in.
"""

from typing import Any

from google.genai import types

# ── Gemini tool schema ────────────────────────────────────────────────────────

GEMINI_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="get_courses",
            description=(
                "Retrieve a list of available courses, optionally filtered by "
                "department code or course level."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "department": types.Schema(
                        type=types.Type.STRING,
                        description="Department code to filter by, e.g. 'CS' or 'MATH'.",
                    ),
                    "level": types.Schema(
                        type=types.Type.INTEGER,
                        description="Course level to filter by, e.g. 3000 for 3000-level courses.",
                    ),
                },
            ),
        ),
        types.FunctionDeclaration(
            name="generate_schedule",
            description=(
                "Generate a weekly course schedule given a list of course IDs "
                "and a target semester."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "courses": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="List of course IDs to include, e.g. ['CS-3001', 'CS-4001'].",
                    ),
                    "semester": types.Schema(
                        type=types.Type.STRING,
                        description="Target semester, e.g. 'Fall 2025'.",
                    ),
                },
                required=["courses"],
            ),
        ),
    ]
)

# ── Mock handler functions ────────────────────────────────────────────────────

def get_courses(department: str = "", level: int = 0) -> dict[str, Any]:
    """Return mock course data. Will be replaced by real DB queries."""
    all_courses = [
        {"id": "CS-3001", "name": "Algorithms", "department": "CS", "level": 3000, "credits": 3},
        {"id": "CS-3002", "name": "Computer Networks", "department": "CS", "level": 3000, "credits": 3},
        {"id": "CS-4001", "name": "Machine Learning", "department": "CS", "level": 4000, "credits": 3},
        {"id": "CS-4002", "name": "Distributed Systems", "department": "CS", "level": 4000, "credits": 3},
        {"id": "MATH-3001", "name": "Linear Algebra", "department": "MATH", "level": 3000, "credits": 4},
    ]

    filtered = all_courses
    if department:
        filtered = [c for c in filtered if c["department"].upper() == department.upper()]
    if level:
        filtered = [c for c in filtered if c["level"] == level]

    return {"courses": filtered}


def generate_schedule(courses: list[str], semester: str = "Fall 2025") -> dict[str, Any]:
    """Return a mock schedule. Will be replaced by real scheduling logic."""
    days_cycle = ["MWF", "TTh", "MWF", "TTh"]
    times_cycle = ["9:00 AM", "10:30 AM", "1:00 PM", "2:30 PM"]

    schedule = [
        {
            "course_id": course_id,
            "days": days_cycle[i % len(days_cycle)],
            "time": times_cycle[i % len(times_cycle)],
        }
        for i, course_id in enumerate(courses)
    ]

    return {"semester": semester, "schedule": schedule}


# ── Dispatch table ────────────────────────────────────────────────────────────

TOOL_HANDLERS: dict[str, Any] = {
    "get_courses": get_courses,
    "generate_schedule": generate_schedule,
}
