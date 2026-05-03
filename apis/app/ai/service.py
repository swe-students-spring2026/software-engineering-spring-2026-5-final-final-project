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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

try:
    from google.genai import types
except Exception:
    types = None  # type: ignore[assignment]

from app.ai.client import MODEL, client as _client
from app.ai.tools import GEMINI_TOOL, TOOL_HANDLERS

# Exposed for tests / external callers; internal code uses _client
client = _client
from app.config.settings import (
    GEMINI_MAX_HISTORY_TURNS,
    GEMINI_MAX_OUTPUT_TOKENS,
    GEMINI_MAX_TOOL_CALL_ROUNDS,
    GEMINI_TEMPERATURE,
    GEMINI_TOP_P,
)


class _MongoEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        try:
            return str(obj)
        except Exception:
            return super().default(obj)


_SYSTEM_INSTRUCTION = (
    "You are an AI Course Selection Assistant for NYU students. "
    "You help students plan their semester by searching the course catalog, "
    "recommending courses, checking prerequisites, and building conflict-free schedules.\n\n"
    "BE PROACTIVE & EFFICIENT: When a student asks for a schedule or course recommendations, "
    "act immediately and return a concrete plan. Use sensible defaults: 4 courses, the "
    "upcoming semester, any time of day. State assumptions briefly, then show real courses.\n\n"
    "ELIGIBILITY (very important):\n"
    "• LOCATION: Recommend ONLY NYC-campus courses (Washington Square or Brooklyn) "
    "  unless the student explicitly mentions a study-away/global campus. The tools "
    "  filter out global campuses by default — keep it that way. If a student does "
    "  ask about NYU London/Paris/Abu Dhabi/etc., set include_study_away=true.\n"
    "• PREREREQUISITES: Every search/section result includes a `prerequisites` field. "
    "  Before recommending a course, READ its prerequisites and check them against "
    "  the student's completed_courses (in the profile context). If a course has "
    "  prerequisites the student has NOT completed, either pick a different course "
    "  or flag the gap explicitly in your response (e.g. 'Note: this requires X, "
    "  which you haven't taken yet'). Do not silently recommend courses the student "
    "  cannot register for.\n"
    "• Many prereq strings are messy/free-text. If unclear, treat ambiguous prereqs "
    "  as a soft warning rather than a hard block.\n\n"
    "TOOL-USE BUDGET — keep tool calls minimal AND batch them:\n"
    "• PARALLELIZE: when the student asks about multiple distinct topics in one message "
    "  (e.g. 'neuroscience AND cybersecurity AND linear algebra'), issue ALL the "
    "  search_courses calls IN A SINGLE TURN as parallel function calls — do NOT call "
    "  them one round at a time. The same applies to get_course_sections for multiple "
    "  candidate courses: batch them in one turn.\n"
    "• Prefer ONE good search_courses call per intended course/topic. Don't fan out 3+ "
    "  redundant searches when the first returned useful results.\n"
    "• Default tool results are slim (code + title only). That's usually enough to pick "
    "  candidates. Only set include_details=true on the final search before recommending.\n"
    "• Call get_course_sections only for courses you actually plan to recommend — don't "
    "  pull sections for everything you found.\n"
    "• Set include_ratings=true on get_course_sections (or call get_professor_profile) "
    "  ONLY when the student explicitly asks about professors or 'best instructors'.\n"
    "• If a search returns nothing, try ONE alternative (drop the term filter, or use "
    "  department-only). Don't keep retrying — explain what you found and ask the user.\n\n"
    "CRITICAL MEMORY LIMITS: You have a strict memory limit. "
    "NEVER call `get_course_sections` or `search_courses` more than 5 times in a single turn. "
    "If you need to build a 4-course schedule, pick exactly 4 candidate courses and "
    "fetch ONLY those 4. Do not fetch a massive list of backups. If you pull too much data, "
    "the system will crash."
    "COURSE NAMES: When a student mentions a course by name ('Data Structures', "
    "'Calculus'), pass that name directly to search_courses or get_course_sections — "
    "you do not need the exact course code.\n\n"
    "FORMATTING: Use markdown. **Bold** course names and key details. Use bullet lists "
    "for options and numbered lists for schedules. Use ## headers to separate sections.\n\n"
    "DATA INTEGRITY: Always use the provided tools to retrieve real data. Never fabricate "
    "course names, codes, meeting times, or requirements. If data is missing, say so."
)

_config = (
    types.GenerateContentConfig(
        tools=[GEMINI_TOOL],
        system_instruction=_SYSTEM_INSTRUCTION,
        temperature=GEMINI_TEMPERATURE,
        top_p=GEMINI_TOP_P,
        max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
    )
    if types is not None
    else None
)


def _execute_tool(name: str, args: dict) -> Any:
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name}"}
    try:
        return handler(**args)
    except Exception as exc:
        return {"error": str(exc)}


def _names_from_items(items: list[Any]) -> list[str]:
    names = [
        str(item.get("title") if isinstance(item, dict) else item).strip()
        for item in items
    ]
    return [n for n in names if n]


def _build_profile_context(
    student_profile: dict[str, Any],
    major_fallback: str,
    completed_fallback: list[str],
) -> str:
    """Render the profile dict into a short prose block prepended to the message."""
    parts: list[str] = []
    current_date = datetime.now().strftime("%B %d, %Y")
    parts.append(f"SYSTEM NOTE: The current date is {current_date}.")
    name = str(student_profile.get("name", "")).strip()
    school = str(student_profile.get("school", "")).strip()
    profile_major = str(student_profile.get("major", "")).strip() or major_fallback
    minor = str(student_profile.get("minor", "")).strip()
    graduation_year = str(student_profile.get("graduation_year", "")).strip()
    completed = student_profile.get("completed_courses") or completed_fallback or []
    current = student_profile.get("current_courses") or []
    major_names = _names_from_items(student_profile.get("majors") or [])
    minor_names = _names_from_items(student_profile.get("minors") or [])

    if name:
        parts.append(f"Student name: {name}")
    if school:
        parts.append(f"Student's school: {school}")
    if profile_major:
        parts.append(f"Student's intended major: {profile_major}")
    if major_names:
        parts.append(f"Student's majors: {', '.join(major_names)}")
    if minor:
        parts.append(f"Student's minor: {minor}")
    if minor_names:
        parts.append(f"Student's minors: {', '.join(minor_names)}")
    if graduation_year:
        parts.append(f"Expected graduation year: {graduation_year}")
    if completed:
        parts.append(f"Completed courses: {', '.join(completed)}")
    if current:
        parts.append(f"Current courses: {', '.join(current)}")

    return "\n".join(parts)


def _history_to_contents(history: list[dict[str, Any]]) -> list[Any]:
    """Convert frontend history ([{role, text}, ...]) into Gemini Content objects.

    Trims to the last GEMINI_MAX_HISTORY_TURNS turns (each turn = 2 messages)
    so the prompt never grows unbounded. Skips empty/invalid entries.
    """
    if not history:
        return []
    cleaned: list[Any] = []
    for entry in history[-(GEMINI_MAX_HISTORY_TURNS * 2):]:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        text = str(entry.get("text") or "").strip()
        if role not in ("user", "model") or not text:
            continue
        cleaned.append(types.Content(
            role=role,
            parts=[types.Part.from_text(text=text)],
        ))
    return cleaned


def _execute_calls_parallel(function_calls: list[Any]) -> list[Any]:
    """Run multiple tool calls in parallel. Each tool is a Mongo query (often
    with an RMP cache lookup), so they're I/O-bound and benefit from threads."""
    if len(function_calls) == 1:
        fc = function_calls[0]
        return [(fc.name, _execute_tool(fc.name, dict(fc.args)))]

    with ThreadPoolExecutor(max_workers=min(len(function_calls), 8)) as ex:
        futures = [
            (fc.name, ex.submit(_execute_tool, fc.name, dict(fc.args)))
            for fc in function_calls
        ]
        return [(name, fut.result()) for name, fut in futures]


def _run_tool_loop(contents: list[Any]) -> str:
    """Drive the generate → tool-call → generate loop until a text answer."""
    response = _client.models.generate_content(
        model=MODEL, contents=contents, config=_config,
    )

    for _ in range(GEMINI_MAX_TOOL_CALL_ROUNDS):
        if not response.function_calls:
            if response.candidates:
                print("DEBUG - AI STOP REASON:", response.candidates[0].finish_reason, flush=True)
            return response.text or ""

        contents.append(response.candidates[0].content)

        results = _execute_calls_parallel(response.function_calls)
        result_parts = [
            types.Part.from_function_response(
                name=name,
                response={"result": json.dumps(result, cls=_MongoEncoder)},
            )
            for name, result in results
        ]
        contents.append(types.Content(role="user", parts=result_parts))

        response = _client.models.generate_content(
            model=MODEL, contents=contents, config=_config,
        )

    if response.function_calls:
        return (
            "I hit a tool-calling limit while building your answer. "
            "Please try narrowing your request (for example, include a department or term)."
        )
    
    if response.candidates:
        print(f"DEBUG - AI STOP REASON: {response.candidates[0].finish_reason}", flush=True)
    return response.text or ""


def chat(
    user_message: str,
    completed_courses: list[str] | None = None,
    major: str = "",
    student_profile: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> str:
    """Run the full tool-calling loop for a single user turn.

    Args:
        user_message: The new user message.
        completed_courses: Fallback list of completed courses if not in profile.
        major: Fallback major if not in profile.
        student_profile: Profile context merged into the prompt.
        history: Prior conversation as [{role: "user"|"model", text: str}, ...].
            Trimmed server-side; safe to pass the whole transcript.
    """
    if _client is None or types is None:
        return (
            "AI chat is not configured. Set GEMINI_API_KEY in your environment "
            "or in the repository .env file and restart the API service."
        )

    profile_block = _build_profile_context(
        student_profile or {},
        major,
        completed_courses or [],
    )

    contents: list[Any] = _history_to_contents(history or [])

    # Profile context goes only on the new turn (not historical ones — they
    # already had their own profile prepended when they were sent originally).
    full_message = f"{profile_block}\n\n{user_message}" if profile_block else user_message
    contents.append(types.Content(
        role="user",
        parts=[types.Part.from_text(text=full_message)],
    ))

    return _run_tool_loop(contents)
