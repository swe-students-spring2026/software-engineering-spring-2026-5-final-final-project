import os
import secrets
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from mongo_store import MongoStore


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_ROOT = BASE_DIR / "output" / "web_jobs"
PIPELINE_SCRIPT = BASE_DIR / "run_pipeline.py"


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(16))
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    store = MongoStore()
    app.config["MONGO_STORE"] = store

    def mongo_ready() -> bool:
        return store.db is not None

    def users_col():
        if store.db is None:
            raise RuntimeError("MongoDB is not configured. Add MONGODB_URI to .env first.")
        return store.db["users"]

    def jobs_col():
        if store.db is None:
            raise RuntimeError("MongoDB is not configured. Add MONGODB_URI to .env first.")
        return store.db["web_jobs"]

    def analysis_sessions_col():
        if store.db is None:
            raise RuntimeError("MongoDB is not configured. Add MONGODB_URI to .env first.")
        return store.db["analysis_sessions"]

    def current_user() -> Optional[dict]:
        user_id = session.get("user_id")
        if not user_id or not mongo_ready():
            return None
        return users_col().find_one({"user_id": user_id})