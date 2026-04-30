"""Shared Gemini client used by the chat loop and the transcript AI fallback."""
from google import genai

from app.config.settings import GEMINI_API_KEY, GEMINI_MODEL

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = GEMINI_MODEL
