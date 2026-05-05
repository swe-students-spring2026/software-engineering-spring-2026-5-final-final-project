"""
Tool definitions and handler functions that query MongoDB.

GEMINI_TOOL contains all function declarations.
TOOL_HANDLERS maps each tool name to its handler.
Call init_tools(db) once at startup to wire in the database.
"""

import re
from typing import Any

from types import SimpleNamespace

# A typical NYU course code looks like "CSCI-UA 101", "MATH-UA 9", "PSYCH-UA 35".
# Used to short-circuit get_course_sections into a fast prefix-match on `code`
# instead of falling back to a slow regex over title/topic.
_COURSE_CODE_RE = re.compile(r"^[A-Z]{2,6}-[A-Z]{1,3}\s*\d", re.IGNORECASE)

try:
    from google.genai import types
except Exception:
    class _FallbackType:
        OBJECT = "object"
        STRING = "string"
        INTEGER = "integer"
        BOOLEAN = "boolean"

    class _FallbackSchema:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class _FallbackTool:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class _FallbackFunctionDeclaration:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    types = SimpleNamespace(
        Type=_FallbackType,
        Schema=_FallbackSchema,
        Tool=_FallbackTool,
        FunctionDeclaration=_FallbackFunctionDeclaration,
    )

from app.services.professor_ratings import build_professor_profile, enrich_classes_with_professor_ratings
from app.services.terms import flexible_term_filter

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
                "department/subject code, or component type. Returns a slim list "
                "(code, title, credits, component) by default — call "
                "get_course_sections for full section details on the courses you pick."
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
                        description="Maximum number of results to return (default 10, hard cap 25).",
                    ),
                    "include_details": types.Schema(
                        type=types.Type.BOOLEAN,
                        description=(
                            "Set to true ONLY when you specifically need course descriptions, "
                            "instructor names, full notes, or professor ratings. Adds "
                            "significant tokens — leave false for browsing/listing. "
                            "(prerequisites and course_location are always returned.)"
                        ),
                    ),
                    "include_study_away": types.Schema(
                        type=types.Type.BOOLEAN,
                        description=(
                            "By default only NYC campuses (Washington Square, Brooklyn) "
                            "are returned because students cannot register for global "
                            "campus (London, Paris, Abu Dhabi, etc.) courses without "
                            "applying to the program. Set true ONLY if the student "
                            "explicitly asks about a study-away/global campus."
                        ),
                    ),
                },
            ),
        ),
        types.FunctionDeclaration(
            name="get_course_sections",
            description=(
                "Get sections for a course by its code or name. Returns slim "
                "section info (code, title, section, instructor, meets_human, "
                "status, component) by default. Accepts a course code like "
                "'CSCI-UA 101' OR a course name/title like 'Data Structures'."
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
                        description="Term code to filter by, e.g. '1268' for Fall 2026.",
                    ),
                    "limit": types.Schema(
                        type=types.Type.INTEGER,
                        description="Max sections to return (default 15, hard cap 30).",
                    ),
                    "include_details": types.Schema(
                        type=types.Type.BOOLEAN,
                        description=(
                            "Set true ONLY if you need raw meeting_times, notes, prereqs, "
                            "or instructional method. Otherwise leave false."
                        ),
                    ),
                    "include_ratings": types.Schema(
                        type=types.Type.BOOLEAN,
                        description=(
                            "Set true ONLY when comparing professors. Adds RMP rating data."
                        ),
                    ),
                    "include_study_away": types.Schema(
                        type=types.Type.BOOLEAN,
                        description=(
                            "Same semantics as on search_courses: defaults to NYC-only. "
                            "Set true only if the student explicitly asks about global campuses."
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
        types.FunctionDeclaration(
            name="get_professor_profile",
            description=(
                "Get a professor's profile including their current course sections and "
                "their Rate My Professors rating when available. Use this when comparing "
                "instructors or optimizing a schedule for better professor ratings."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "name": types.Schema(
                        type=types.Type.STRING,
                        description="Professor name, in either 'First Last' or 'Last, First' format.",
                    ),
                    "term": types.Schema(
                        type=types.Type.STRING,
                        description="Optional term code to restrict the taught-course list.",
                    ),
                },
                required=["name"],
            ),
        ),
    ]
)


# ── Handler functions ─────────────────────────────────────────────────────────

# NYC-campus locations. Anything else is study-away (London, Paris, Abu Dhabi,
# etc.) — students can't normally register for those, so we filter them out
# of search results by default unless include_study_away=true.
_NYC_LOCATIONS = ["Washington Square", "Brooklyn Campus"]

_SLIM_COURSE_PROJECTION = {
    "_id": 0, "code": 1, "title": 1, "credits": 1,
    "subject_code": 1, "component": 1, "term": 1, "topic": 1,
    "course_location": 1, "prerequisites": 1,
}

_DETAILED_COURSE_PROJECTION = {
    "_id": 0, "code": 1, "title": 1, "description": 1, "credits": 1,
    "school": 1, "subject_code": 1, "component": 1, "section": 1,
    "crn": 1, "instructor": 1, "meets_human": 1, "status": 1,
    "term": 1, "topic": 1, "prerequisites": 1, "course_location": 1, "notes": 1,
}


def _build_search_filter(
    query: str, department: str, term: str, component: str, include_study_away: bool,
) -> dict:
    conditions: list[dict] = []
    if not include_study_away:
        conditions.append({"course_location": {"$in": _NYC_LOCATIONS}})
    if term:
        conditions.append(flexible_term_filter(term))
    if component:
        conditions.append({"component": component})
    if department:
        conditions.append({"$or": [
            {"subject_code": {"$regex": department, "$options": "i"}},
            {"code": {"$regex": department, "$options": "i"}},
        ]})
    if query:
        conditions.append({"$text": {"$search": query}})

    if len(conditions) > 1:
        return {"$and": conditions}
    if conditions:
        return conditions[0]
    return {}


def _dedupe_by_code(courses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for c in courses:
        key = c.get("code") or ""
        if key and key in seen:
            continue
        seen.add(key)
        unique.append(c)
    return unique


def search_courses(
    query: str = "",
    department: str = "",
    term: str = "",
    component: str = "",
    limit: int = 10,
    include_details: bool = False,
    include_study_away: bool = False,
) -> dict[str, Any]:
    """Search course catalog in MongoDB. Uses $text index for keyword queries.

    By default returns a slim payload (code, title, credits, component, term,
    course_location) and EXCLUDES NYU study-away campuses (London, Paris, Abu
    Dhabi, etc.) since students can't typically register for those without
    applying to the program. Pass include_study_away=true if explicitly asked
    about a global campus. Pass include_details=true for descriptions,
    prerequisites, notes, and professor ratings.
    """
    if _db is None:
        return {"error": "Database not initialized"}

    filter_query = _build_search_filter(query, department, term, component, include_study_away)
    safe_limit = max(1, min(int(limit) if limit else 10, 25))
    projection = _DETAILED_COURSE_PROJECTION if include_details else _SLIM_COURSE_PROJECTION

    # Catalog has multiple section rows per course code, so dedup-after-limit
    # systematically under-counted. Fetch a buffer (cap 75 — slim projection
    # keeps each row tiny), dedupe by code, then trim to the requested limit.
    fetch_limit = min(safe_limit * 3, 75)
    courses = list(_db.classes.find(filter_query, projection).limit(fetch_limit))
    unique = _dedupe_by_code(courses)[:safe_limit]

    if include_details:
        unique = enrich_classes_with_professor_ratings(unique)
    return {"courses": unique, "count": len(unique)}


# Slim sections still include course_location + prerequisites so the model
# can sanity-check eligibility without a second round-trip.
_SLIM_SECTION_PROJECTION = {
    "_id": 0, "code": 1, "title": 1, "section": 1, "crn": 1,
    "instructor": 1, "meets_human": 1, "status": 1,
    "component": 1, "credits": 1, "topic": 1,
    "course_location": 1, "prerequisites": 1,
}

_DETAILED_SECTION_PROJECTION = {
    "_id": 0, "code": 1, "title": 1, "section": 1, "crn": 1,
    "instructor": 1, "meets_human": 1, "meeting_times": 1,
    "status": 1, "component": 1, "instructional_method": 1,
    "campus_location": 1, "course_location": 1, "credits": 1, "topic": 1,
    "notes": 1, "prerequisites": 1,
}


def get_course_sections(
    course_code: str,
    term: str = "",
    limit: int = 15,
    include_details: bool = False,
    include_ratings: bool = False,
    include_study_away: bool = False,
) -> dict[str, Any]:
    """Get sections matching a course code or title from MongoDB.

    By default returns a slim payload (no raw meeting_times, no notes), with
    up to 15 sections, and EXCLUDES NYU study-away campuses. Each result
    includes course_location + prerequisites so you can verify eligibility.
    Pass include_details=True for full section data, include_ratings=True for
    professor ratings, include_study_away=True to allow global campuses.
    """
    if _db is None:
        return {"error": "Database not initialized"}

    raw = (course_code or "").strip()
    escaped = re.escape(raw)

    # Fast path: when input looks like a course code (e.g. "CSCI-UA 101"),
    # match `code` only with an anchored regex so MongoDB can use a prefix
    # index. The unanchored regex over code/title/topic was forcing collection
    # scans; this avoids that for ~all model-issued lookups, which pass codes.
    if _COURSE_CODE_RE.match(raw):
        primary = {"code": {"$regex": f"^{escaped}", "$options": "i"}}
    else:
        # Fallback: keyword-style lookup over title/topic, plus an anchored
        # `code` match in case the user passed a partial code. Still regex,
        # but the OR is narrower than before.
        primary = {"$or": [
            {"code": {"$regex": f"^{escaped}", "$options": "i"}},
            {"title": {"$regex": escaped, "$options": "i"}},
            {"topic": {"$regex": escaped, "$options": "i"}},
        ]}

    conditions: list[dict] = [primary]
    if term:
        conditions.append(flexible_term_filter(term))
    if not include_study_away:
        conditions.append({"course_location": {"$in": _NYC_LOCATIONS}})
    query: dict = {"$and": conditions} if len(conditions) > 1 else conditions[0]

    safe_limit = max(1, min(int(limit) if limit else 15, 30))
    projection = _DETAILED_SECTION_PROJECTION if include_details else _SLIM_SECTION_PROJECTION

    sections = list(_db.classes.find(query, projection).limit(safe_limit))

    if include_ratings:
        sections = enrich_classes_with_professor_ratings(sections)
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


def verify_section_crns(pairs: list[tuple[str, str]]) -> set[tuple[str, str]]:
    """Return the subset of (code, crn) pairs that actually exist in the catalog.

    Used to validate the AI's `add-courses` block before sending the reply to
    the frontend, since the model occasionally fabricates CRNs that match its
    prose but don't exist in MongoDB.
    """
    if _db is None or not pairs:
        return set()

    or_clauses = [{"code": code, "crn": crn} for code, crn in pairs if code and crn]
    if not or_clauses:
        return set()

    cursor = _db.classes.find({"$or": or_clauses}, {"_id": 0, "code": 1, "crn": 1})
    return {(str(row.get("code", "")), str(row.get("crn", ""))) for row in cursor}


def get_professor_profile(name: str, term: str = "") -> dict[str, Any]:
    if _db is None:
        return {"error": "Database not initialized"}

    profile = build_professor_profile(_db, name, term)
    if not profile:
        return {"error": f"Professor not found: {name}"}
    return profile


# ── Dispatch table ────────────────────────────────────────────────────────────

TOOL_HANDLERS: dict[str, Any] = {
    "search_courses": search_courses,
    "get_course_sections": get_course_sections,
    "list_programs": list_programs,
    "get_program_requirements": get_program_requirements,
    "get_professor_profile": get_professor_profile,
}
