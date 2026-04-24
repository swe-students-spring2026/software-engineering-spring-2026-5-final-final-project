import os

from dotenv import load_dotenv

# load_dotenv() is a no-op when env vars are already set (e.g. in Docker),
# and searches upward from cwd for .env when running locally.
load_dotenv(override=False)

GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

if not GEMINI_API_KEY:
    raise EnvironmentError("GEMINI_API_KEY is not set. Add it to your .env file.")
