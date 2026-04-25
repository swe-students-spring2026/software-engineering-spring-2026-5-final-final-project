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
from typing import Any

from google import genai
from google.genai import types

from app.config.settings import GEMINI_API_KEY, GEMINI_MODEL
from app.ai.tools import GEMINI_TOOL, TOOL_HANDLERS


class _MongoEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        try:
            # handles bson.ObjectId without a hard import
            return str(obj)
        except Exception:
            return super().default(obj)

_client = genai.Client(api_key=GEMINI_API_KEY)

_SYSTEM_INSTRUCTION = (
    "You are an AI Course Selection Assistant for NYU students. "
    "You help students plan their semester by searching the course catalog, "
    "recommending courses, checking prerequisites, and building conflict-free schedules.\n\n"
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
) -> str:
    """
    Run the full tool-calling loop for a single user turn.

    Returns the model's final plain-text reply.
    """
    context_parts: list[str] = []
    if major:
        context_parts.append(f"Student's intended major: {major}")
    if completed_courses:
        context_parts.append(
            f"Completed courses: {', '.join(completed_courses)}"
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
        model=GEMINI_MODEL,
        contents=contents,
        config=_config,
    )

    # Keep looping as long as the model wants to call tools.
    while response.function_calls:
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
            model=GEMINI_MODEL,
            contents=contents,
            config=_config,
        )

    return response.text or ""
