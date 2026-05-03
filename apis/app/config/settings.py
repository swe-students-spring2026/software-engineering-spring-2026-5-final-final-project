import os

from dotenv import load_dotenv

# load_dotenv() is a no-op when env vars are already set (e.g. in Docker),
# and searches upward from cwd for .env when running locally.
load_dotenv(override=False)

GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


GEMINI_TEMPERATURE: float = _env_float("GEMINI_TEMPERATURE", 0.2)
GEMINI_TOP_P: float = _env_float("GEMINI_TOP_P", 0.9)
GEMINI_MAX_OUTPUT_TOKENS: int = _env_int("GEMINI_MAX_OUTPUT_TOKENS", 4096)
GEMINI_MAX_TOOL_CALL_ROUNDS: int = _env_int("GEMINI_MAX_TOOL_CALL_ROUNDS", 16)
# Max prior conversation turns kept in chat context (each turn = user msg + AI reply)
GEMINI_MAX_HISTORY_TURNS: int = _env_int("GEMINI_MAX_HISTORY_TURNS", 10)
# Cap reasoning tokens for Gemini 2.5 thinking models. 0 disables thinking,
# -1 lets the model decide (its default), positive caps to that many tokens.
# 512 is a low-but-not-zero ceiling — keeps a bit of multi-step reasoning for
# tool-call planning without paying for many seconds of hidden thought.
GEMINI_THINKING_BUDGET: int = _env_int("GEMINI_THINKING_BUDGET", 512)
