import os

from dotenv import load_dotenv

# load_dotenv() is a no-op when env vars are already set (e.g. in Docker),
# and searches upward from cwd for .env when running locally.
load_dotenv(override=False)

def _env_str(name: str, default: str) -> str:
    """Like os.environ.get but treats an empty string as unset.

    docker-compose's `${VAR:-}` expansion passes "" when the variable isn't
    in `.env`, which would otherwise clobber our in-code defaults. Also
    strips inline `# comment` text in case someone pasted a commented value
    into `.env` (python-dotenv does honor inline comments, but only when
    preceded by whitespace; we belt-and-braces it here so a bare `value#…`
    doesn't sneak through either).
    """
    value = os.environ.get(name, "")
    if "#" in value:
        value = value.split("#", 1)[0]
    value = value.strip()
    return value or default


GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL: str = _env_str("GEMINI_MODEL", "gemini-2.5-flash")

# Per-request model selector. Frontend sends one of these labels; the route
# maps it to a real model ID. Whitelisting (by tier name, not model ID)
# prevents arbitrary model names from being passed to the API. Each tier
# can be overridden independently via env vars; otherwise sensible defaults
# apply. GEMINI_MODEL is the fallback for the Balanced tier.
GEMINI_MODEL_CHOICES: dict[str, str] = {
    "fast":     _env_str("GEMINI_MODEL_FAST",     "gemini-2.5-flash-lite"),
    "balanced": _env_str("GEMINI_MODEL_BALANCED", GEMINI_MODEL),
    "smart":    _env_str("GEMINI_MODEL_SMART",    "gemini-2.5-pro"),
}


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
