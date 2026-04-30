"""Shared Gemini client used by the chat loop and the transcript AI fallback."""
try:
    from google import genai
    from app.config.settings import GEMINI_API_KEY, GEMINI_MODEL
    client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
    MODEL = GEMINI_MODEL
except Exception:
    client = None
    MODEL = ""
