"""
Gemini client and tool-calling loop.

Flow:
  1. Send user message to Gemini via generate_content().
  2. If the model returns function_calls, execute them via TOOL_HANDLERS.
  3. Append model response + tool results to contents and resend.
  4. Repeat until no more function calls, then return the final text.
"""

import json
from typing import Any

from google import genai
from google.genai import types

from app.config.settings import GEMINI_API_KEY, GEMINI_MODEL
from app.ai.tools import GEMINI_TOOL, TOOL_HANDLERS

_client = genai.Client(api_key=GEMINI_API_KEY)
_config = types.GenerateContentConfig(tools=[GEMINI_TOOL])


def _execute_tool(name: str, args: dict) -> Any:
    """Call the matching handler; args is already a dict from Gemini."""
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name}"}
    try:
        return handler(**args)
    except Exception as exc:
        return {"error": str(exc)}


def chat(user_message: str) -> str:
    """
    Run the full tool-calling loop for a single user turn.

    Returns the model's final plain-text reply.
    """
    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part.from_text(user_message)])
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

        # Execute each tool call and collect the results as function response parts.
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
