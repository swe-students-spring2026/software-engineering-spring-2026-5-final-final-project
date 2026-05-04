import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
MOCK_MODE = os.environ.get("MOCK_MODE", "false").lower() == "true"
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")
