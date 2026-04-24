import os
from pathlib import Path

from flask import Flask, jsonify, request
from pymongo import MongoClient
from dotenv import load_dotenv

try:
    from apis.app.services.requirements_service import RequirementsService
except ModuleNotFoundError:
    from services.requirements_service import RequirementsService

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

app = Flask(__name__)

mongo_uri = os.getenv("MONGO_URI")
mongo_db_name = os.getenv("MONGO_DB_NAME")

if not mongo_uri or not mongo_db_name:
    raise RuntimeError(
        "Missing MongoDB configuration. Set MONGO_URI and MONGO_DB_NAME in the "
        "environment or in the repo root .env file."
    )

client = MongoClient(mongo_uri)
db = client[mongo_db_name]
requirements_service = RequirementsService()


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "apis"})


@app.get("/classes")
def get_classes():
    term = request.args.get("term")
    q = request.args.get("q")
    query = {}
    if term:
        query["term.code"] = term
    if q:
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"code": {"$regex": q, "$options": "i"}},
            {"subject_code": {"$regex": q, "$options": "i"}},
            {"instructor": {"$regex": q, "$options": "i"}},
        ]
    classes = list(db.classes.find(query, {"_id": 0, "_details_raw": 0}))
    return jsonify(classes)


@app.get("/programs")
def get_programs():
    programs = requirements_service.list_undergraduate_programs()
    return jsonify(programs)


@app.get("/program-requirements")
def get_program_requirements():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "missing required query parameter: url"}), 400

    program = requirements_service.fetch_program_requirements(url)
    return jsonify(program)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("API_INTERNAL_PORT", "8000")))
