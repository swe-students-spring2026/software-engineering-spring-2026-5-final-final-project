import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from pymongo import MongoClient

try:
    from apis.app.services.requirements_service import RequirementsService
except ModuleNotFoundError:
    from services.requirements_service import RequirementsService

try:
    from scrapers.scraper import refresh_course_document
except ModuleNotFoundError:
    refresh_course_document = None

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.routes.chat import chat_bp

app = Flask(__name__)
app.register_blueprint(chat_bp)

mongo_uri = os.getenv("MONGO_URI")
mongo_db_name = os.getenv("MONGO_DB_NAME")

if not mongo_uri or not mongo_db_name:
    raise RuntimeError(
        "Missing MongoDB configuration. Set MONGO_URI and MONGO_DB_NAME in the "
        "environment or in the repo root .env file."
    )

client = MongoClient(mongo_uri)
db = client[mongo_db_name]
requirements_service = RequirementsService(db)


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

    classes = list(db.classes.find(query))
    return jsonify(classes)


@app.post("/classes/refresh")
def refresh_class():
    if refresh_course_document is None:
        return jsonify({"error": "course refresh is not available in this runtime"}), 503

    payload = request.get_json(silent=True) or {}
    term = payload.get("term") or request.args.get("term")
    class_id = payload.get("_id") or request.args.get("_id")
    code = payload.get("code") or request.args.get("code")
    crn = payload.get("crn") or request.args.get("crn")
    section = payload.get("section") or request.args.get("section")

    existing = None
    if class_id:
        existing = db.classes.find_one({"_id": class_id})
    elif term and crn:
        existing = db.classes.find_one({"term.code": term, "crn": str(crn)})

    if existing:
        term = term or existing.get("term", {}).get("code")
        code = code or existing.get("code")
        crn = crn or existing.get("crn")
        section = section or existing.get("section")

    if not term or not code:
        return jsonify({"error": "provide term and either _id or code (optionally crn/section)"}), 400

    refreshed = refresh_course_document(term, code=code, crn=crn, section=section)

    if not refreshed:
        return jsonify({"error": "course could not be refreshed"}), 404

    db.classes.update_one({"_id": refreshed["_id"]}, {"$set": refreshed}, upsert=True)

    return jsonify(
        {key: value for key, value in refreshed.items() if key != "_details_raw"}
    )


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

    if not program:
        return jsonify({"error": "program not found"}), 404

    return jsonify(program)


if __name__ == "__main__":
    port = int(os.environ.get("PORT") or os.environ.get("API_INTERNAL_PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
