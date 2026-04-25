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
from typing import Any

from google import genai
from google.genai import types

from app.config.settings import GEMINI_API_KEY, GEMINI_MODEL
from app.ai.tools import GEMINI_TOOL, TOOL_HANDLERS

_client = genai.Client(api_key=GEMINI_API_KEY)

_SYSTEM_INSTRUCTION = (
    "You are an AI Course Selection Assistant for NYU students. "
    "You help students plan their semester by:\n"
    "- Searching the NYU course catalog for available courses\n"
    "- Recommending courses based on completed courses and degree requirements\n"
    "- Identifying prerequisite requirements and checking whether they are met\n"
    "- Detecting and avoiding schedule conflicts\n"
    "- Explaining degree requirements for specific programs\n\n"
    "Always use the provided tools to retrieve real course and program data. "
    "Never fabricate course names, codes, meeting times, or degree requirements. "
    "When making recommendations, explain your reasoning and cite retrieved data. "
    "If data is incomplete or a major is not supported, say so honestly."
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
                    response={"result": json.dumps(result)},
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
