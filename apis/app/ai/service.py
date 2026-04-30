"""
Gemini client and tool-calling loop.

Flow:
  1. Build initial contents with optional student context (major, completed courses).
  2. Send to Gemini via generate_content().
  3. If the model returns function_calls, execute them via TOOL_HANDLERS.
  4. Append model response + tool results to contents and resend.
  5. Repeat until no more function calls, then return the final text.
"""

import json
from datetime import datetime
from types import SimpleNamespace
from typing import Any

from unittest.mock import MagicMock

try:
    from google import genai
    from google.genai import types
    _GENAI_AVAILABLE = True
except Exception:
    _GENAI_AVAILABLE = False

    class _FallbackPart:
        from_text = MagicMock()
        from_function_response = MagicMock()

    class _FallbackTypes:
        Part = _FallbackPart
        Content = lambda self=None, **kwargs: SimpleNamespace(**kwargs)
        GenerateContentConfig = lambda self=None, **kwargs: SimpleNamespace(**kwargs)

    class _FallbackModels:
        def generate_content(self, *args, **kwargs):
            raise RuntimeError("Gemini SDK is unavailable in this environment.")

    class _FallbackClient:
        def __init__(self, *args, **kwargs):
            self.models = _FallbackModels()

    genai = SimpleNamespace(Client=_FallbackClient)
    types = _FallbackTypes()

from app.config.settings import (
    GEMINI_API_KEY,
    GEMINI_MAX_OUTPUT_TOKENS,
    GEMINI_MAX_TOOL_CALL_ROUNDS,
    GEMINI_MODEL,
    GEMINI_TEMPERATURE,
    GEMINI_TOP_P,
)
from app.ai.tools import GEMINI_TOOL, TOOL_HANDLERS

MODEL = GEMINI_MODEL


class _MongoEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        try:
            # handles bson.ObjectId without a hard import
            return str(obj)
        except Exception:
            return super().default(obj)

_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY and _GENAI_AVAILABLE else None
# Backwards-compatible alias (tests and other modules may import `client`)
client = _client

_SYSTEM_INSTRUCTION = (
    "You are an AI Course Selection Assistant for NYU students. "
    "You help students plan their semester by searching the course catalog, "
    "recommending courses, checking prerequisites, and building conflict-free schedules.\n\n"
    "PROFESSOR QUALITY: If the student asks for the best professors, highest-rated instructors, "
    "or to maximize professor quality, you should actively use professor-rating data from the "
    "available tools. Compare instructor ratings before finalizing recommendations, and prefer "
    "higher-rated instructors when the schedule remains academically sensible.\n\n"
    "BE PROACTIVE: When a student asks for a schedule or course recommendations, "
    "act immediately — search the database right away and return a concrete plan. "
    "Do NOT ask unnecessary clarifying questions. Use sensible defaults: "
    "recommend 4 courses, use the upcoming semester, any time of day is fine. "
    "State your assumptions briefly, then show the actual courses and sections.\n\n"
    "SEARCH STRATEGY — follow this order before giving up:\n"
    "1. Try search_courses with a keyword AND a term code.\n"
    "2. If that returns fewer than 4 results, retry WITHOUT the term filter to widen the pool.\n"
    "3. If a keyword search fails, try search_courses with just the department code "
    "(e.g. department='CSCI', department='MATH', department='ECON') to list ALL courses "
    "in that department, then pick from those results.\n"
    "4. If the student wants a full schedule, run multiple searches across different "
    "departments/topics to gather enough courses — do not stop at one search call.\n"
    "5. Only after exhausting the above should you report limited data, and even then "
    "present whatever courses were found rather than returning an empty-handed response.\n\n"
    "6. When comparing multiple sections or instructors, inspect their professor rating data. "
    "If needed, call get_professor_profile for the finalists you are considering.\n\n"
    "NEVER give up after a single failed search. Always try at least 2–3 different "
    "search strategies (different keywords, no term filter, department-only) before "
    "concluding that a course does not exist in the catalog.\n\n"
    "COURSE NAMES: When a student mentions a course by name (e.g. 'Data Structures', "
    "'Calculus', 'Operating Systems'), pass that name directly to search_courses or "
    "get_course_sections — you do not need the exact course code.\n\n"
    "FORMATTING: Always format your responses with markdown. "
    "Use **bold** for course names and key details. "
    "Use bullet lists for course options and numbered lists for schedules. "
    "Use headers (##) to separate sections like Recommended Courses and Schedule.\n\n"
    "DATA INTEGRITY: Always use the provided tools to retrieve real data. "
    "Never fabricate course names, codes, meeting times, or requirements. "
    "If data is missing or a major is unsupported, say so honestly."
)

_config = types.GenerateContentConfig(
    tools=[GEMINI_TOOL],
    system_instruction=_SYSTEM_INSTRUCTION,
    temperature=GEMINI_TEMPERATURE,
    top_p=GEMINI_TOP_P,
    max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
)


def _execute_tool(name: str, args: dict) -> Any:
    """Call the matching handler; args is already a dict from Gemini."""
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name}"}
    try:
        return handler(**args)
    except Exception as exc:
        return {"error": str(exc)}


def chat(
    user_message: str,
    completed_courses: list[str] | None = None,
    major: str = "",
    student_profile: dict[str, Any] | None = None,
) -> str:
    """
    Run the full tool-calling loop for a single user turn.

    Returns the model's final plain-text reply.
    """
    if _client is None:
        return (
            "AI chat is not configured. Set GEMINI_API_KEY in your environment "
            "or in the repository .env file and restart the API service."
        )

    student_profile = student_profile or {}
    context_parts: list[str] = []

    name = str(student_profile.get("name", "")).strip()
    school = str(student_profile.get("school", "")).strip()
    profile_major = str(student_profile.get("major", "")).strip() or major
    minor = str(student_profile.get("minor", "")).strip()
    graduation_year = str(student_profile.get("graduation_year", "")).strip()
    profile_completed_courses = student_profile.get("completed_courses") or completed_courses or []
    current_courses = student_profile.get("current_courses") or []

    if name:
        context_parts.append(f"Student name: {name}")
    if school:
        context_parts.append(f"Student's school: {school}")
    if profile_major:
        context_parts.append(f"Student's intended major: {profile_major}")
    if minor:
        context_parts.append(f"Student's minor: {minor}")
    if graduation_year:
        context_parts.append(f"Expected graduation year: {graduation_year}")
    if profile_completed_courses:
        context_parts.append(
            f"Completed courses: {', '.join(profile_completed_courses)}"
        )
    if current_courses:
        context_parts.append(
            f"Current courses: {', '.join(current_courses)}"
        )

    if context_parts:
        full_message = "\n".join(context_parts) + "\n\n" + user_message
    else:
        full_message = user_message

    contents: list[types.Content] = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=full_message)],
        )
    ]

    response = _client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=_config,
    )

    # Keep looping as long as the model wants to call tools.
    rounds = 0
    while response.function_calls:
        rounds += 1
        if rounds > GEMINI_MAX_TOOL_CALL_ROUNDS:
            return (
                "I hit a tool-calling limit while building your answer. "
                "Please try narrowing your request (for example, include a department or term)."
            )

        # Add model's response (contains the function_call parts) to history.
        contents.append(response.candidates[0].content)

        # Execute each tool call and collect results as function response parts.
        result_parts: list[types.Part] = []
        for fc in response.function_calls:
            result = _execute_tool(fc.name, dict(fc.args))
            result_parts.append(
                types.Part.from_function_response(
                    name=fc.name,
                    response={"result": json.dumps(result, cls=_MongoEncoder)},
                )
            )

        # Append tool results and call the model again.
        contents.append(types.Content(role="user", parts=result_parts))

        response = _client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=_config,
        )

    return response.text or ""
