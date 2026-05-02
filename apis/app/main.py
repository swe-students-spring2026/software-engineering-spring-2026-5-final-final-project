import io
import logging
import math
import os
import re
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from pymongo import MongoClient
from werkzeug.security import check_password_hash, generate_password_hash

logger = logging.getLogger(__name__)

try:
    from apis.app.services.requirements_service import RequirementsService
    from apis.app.services.professor_ratings import (
        build_professor_profile,
        enrich_classes_with_professor_ratings,
        init_professor_ratings,
        search_professors,
    )
    from apis.app.services.terms import class_term_filter
except ModuleNotFoundError:
    from app.services.requirements_service import RequirementsService
    from app.services.professor_ratings import (
        build_professor_profile,
        enrich_classes_with_professor_ratings,
        init_professor_ratings,
        search_professors,
    )
    from app.services.terms import class_term_filter

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.routes.chat import chat_bp

app = Flask(__name__)
app.register_blueprint(chat_bp)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB upload limit

mongo_uri = os.getenv("MONGO_URI")
mongo_db_name = os.getenv("MONGO_DB_NAME")
internal_api_token = os.getenv("API_INTERNAL_TOKEN", "")

if not mongo_uri or not mongo_db_name:
    raise RuntimeError(
        "Missing MongoDB configuration. Set MONGO_URI and MONGO_DB_NAME in the "
        "environment or in the repo root .env file."
    )

client = MongoClient(mongo_uri)
db = client[mongo_db_name]
requirements_service = RequirementsService(db)

# Wire professor ratings MongoDB cache and AI tools
init_professor_ratings(db)
db.users.create_index("email", unique=True, background=True)

from app.ai.tools import init_tools  # noqa: E402
init_tools(db)


ALBERT_CLASS_COLLECTION = "classes"
BULLETIN_CLASS_COLLECTION = "bulletin_classes"


try:
    from scrapers.scraper import refresh_course_document as _BULLETIN_REFRESH
except ModuleNotFoundError:
    try:
        from scraper import refresh_course_document as _BULLETIN_REFRESH
    except ModuleNotFoundError:
        logger.error(
            "Bulletin scraper module not found at startup; the per-course reload "
            "button (/classes/reload) will return 503 until scrapers/ is on the path."
        )
        _BULLETIN_REFRESH = None


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "apis",
        "bulletin_refresh_available": _BULLETIN_REFRESH is not None,
    })


def _class_collection(source: str):
    if source == "bulletin":
        return db[BULLETIN_CLASS_COLLECTION]
    return db.classes


def _term_filter(term: str, source: str) -> dict[str, Any]:
    return class_term_filter(term, source)


def _require_internal_api_token():
    if not internal_api_token:
        return jsonify({"error": "API_INTERNAL_TOKEN is not configured"}), 503
    if request.headers.get("X-Internal-API-Token") != internal_api_token:
        return jsonify({"error": "forbidden"}), 403
    return None


def _prepare_class_response(doc: dict[str, Any]) -> dict[str, Any]:
    course = dict(doc)
    course.pop("source", None)
    return course


@app.get("/classes")
def get_classes():
    term      = request.args.get("term")
    q         = request.args.get("q")
    school    = request.args.get("school")
    component = request.args.get("component")
    status    = request.args.get("status")
    source    = request.args.get("source", "albert").strip().lower()
    page      = max(1, request.args.get("page", default=1, type=int))
    page_size = 20

    if source not in {"albert", "bulletin"}:
        return jsonify({"error": "source must be either 'albert' or 'bulletin'"}), 400

    collection = _class_collection(source)
    query: dict = {}

    if term:
        query.update(_term_filter(term, source))
    if school:
        # School values come from the /classes/schools dropdown — exact match
        query["school"] = school
    if component:
        # Component values come from a controlled dropdown — exact match
        query["component"] = component
    if status == "open":
        query["status"] = "Open"
    elif status == "closed":
        query["status"] = "Closed"
    elif status == "waitlist":
        query["status"] = {"$regex": r"^wait", "$options": "i"}
    if q:
        instructor_pattern = ".*".join(re.escape(t) for t in q.split())
        query["$or"] = [
            {"title":        {"$regex": re.escape(q), "$options": "i"}},
            {"code":         {"$regex": re.escape(q), "$options": "i"}},
            {"subject_code": {"$regex": re.escape(q), "$options": "i"}},
            {"instructor":   {"$regex": instructor_pattern, "$options": "i"}},
        ]

    pipeline = [
        {"$match": query},
        {"$group": {"_id": "$code"}},
        {"$sort": {"_id": 1}},
        {"$facet": {
            "total":      [{"$count": "n"}],
            "page_codes": [
                {"$skip": (page - 1) * page_size},
                {"$limit": page_size},
            ],
        }},
    ]
    facet_result = next(iter(collection.aggregate(pipeline)), {"total": [], "page_codes": []})
    total_courses = facet_result["total"][0]["n"] if facet_result["total"] else 0
    total_pages = math.ceil(total_courses / page_size) if total_courses > 0 else 1
    page_codes = [row["_id"] for row in facet_result["page_codes"]]

    # Keep original filters when expanding paginated course codes to sections.
    if page_codes:
        code_filter = {"code": {"$in": page_codes}}
        section_query = {"$and": [query, code_filter]} if query else code_filter
        cursor = collection.find(section_query, {"_id": 0, "source": 0})
        cursor_sort = getattr(cursor, "sort", None)
        if callable(cursor_sort) and not isinstance(cursor, list):
            cursor = cursor_sort([
                ("code", 1),
                ("section", 1),
                ("component", 1),
            ])
        classes = [_prepare_class_response(course) for course in cursor]
    else:
        classes = []
    classes = enrich_classes_with_professor_ratings(classes)
    return jsonify({
        "classes": classes,
        "total_courses": total_courses,
        "page": page,
        "total_pages": total_pages,
        "source": source,
    })


@app.post("/classes/reload")
def reload_class_from_bulletin():
    auth_error = _require_internal_api_token()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    term = str(data.get("term", "")).strip()
    code = str(data.get("code", "")).strip()
    crn = str(data.get("crn", "")).strip() or None
    section = str(data.get("section", "")).strip() or None

    if not term or not code:
        return jsonify({"error": "term and code are required"}), 400

    if _BULLETIN_REFRESH is None:
        return jsonify({"error": "bulletin scraper is unavailable"}), 503

    doc = _BULLETIN_REFRESH(term, code=code, crn=crn, section=section)
    if not doc:
        return jsonify({"error": "course not found in bulletin data"}), 404

    db[BULLETIN_CLASS_COLLECTION].update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
    doc = {key: value for key, value in doc.items() if key not in {"_id", "source"}}
    return jsonify({"course": doc, "source": "bulletin"}), 200


# Simple TTL cache for the schools list (refreshes every 5 minutes)
_schools_cache: list | None = None
_schools_cache_ts: float = 0.0
_SCHOOLS_CACHE_TTL = 300.0


@app.get("/classes/schools")
def get_schools():
    global _schools_cache, _schools_cache_ts
    now = time.monotonic()
    if _schools_cache is None or now - _schools_cache_ts > _SCHOOLS_CACHE_TTL:
        _schools_cache = sorted(s for s in db.classes.distinct("school") if s)
        _schools_cache_ts = now
    return jsonify(_schools_cache)


@app.get("/professors")
def get_professors():
    q = request.args.get("q", "").strip()
    term = request.args.get("term", "").strip()
    limit = request.args.get("limit", default=20, type=int)
    return jsonify(search_professors(db, query=q, term=term, limit=max(1, min(limit, 100))))


@app.get("/professors/profile")
def get_professor_profile():
    name = request.args.get("name", "").strip()
    term = request.args.get("term", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    profile = build_professor_profile(db, name, term)
    if not profile:
        return jsonify({"error": "professor not found"}), 404
    return jsonify(profile)


@app.get("/classes/campuses")
def get_campuses():
    return jsonify([])


@app.post("/auth/register")
def auth_register():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    name = data.get("name", "").strip()

    if not email.endswith("@nyu.edu"):
        return jsonify({"error": "Only @nyu.edu email addresses are allowed."}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400
    if db.users.find_one({"email": email}):
        return jsonify({"error": "An account with this email already exists."}), 409

    db.users.insert_one({"email": email, "name": name, "password": generate_password_hash(password)})
    return jsonify({"message": "Account created successfully."}), 201


@app.post("/auth/login")
def auth_login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = db.users.find_one({"email": email})
    if not user or not user.get("password") or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid email or password."}), 401

    return jsonify({"name": user.get("name", email)}), 200


@app.post("/auth/google")
def auth_google_upsert():
    auth_error = _require_internal_api_token()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    name = data.get("name", "").strip()

    if not email.endswith("@nyu.edu"):
        return jsonify({"error": "Only @nyu.edu Google accounts are allowed."}), 400

    db.users.update_one(
        {"email": email},
        {"$set": {"email": email, "name": name, "google_auth": True}},
        upsert=True,
    )
    return jsonify({"message": "ok"}), 200


@app.get("/user/profile")
def get_profile():
    auth_error = _require_internal_api_token()
    if auth_error:
        return auth_error

    email = request.args.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "email required"}), 400
    user = db.users.find_one({"email": email}, {"_id": 0, "password": 0})
    if not user:
        return jsonify({"error": "user not found"}), 404
    transcript_raw = user.get("transcript_raw", "")
    if transcript_raw and not user.get("test_credits") and not user.get("test_credit_total"):
        from app.services.transcript_parser import parse_test_credits
        parsed_test_credits = parse_test_credits(transcript_raw)
        if parsed_test_credits["test_credits"] or parsed_test_credits["test_credit_total"]:
            user.update(parsed_test_credits)
            db.users.update_one({"email": email}, {"$set": parsed_test_credits})
    user.pop("transcript_raw", None)
    return jsonify(user)


@app.put("/user/profile")
def update_profile():
    auth_error = _require_internal_api_token()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "email required"}), 400

    allowed = {
        "name",
        "major",
        "major_url",
        "majors",
        "school",
        "minor",
        "minors",
        "graduation_year",
        "student_id",
        "completed_courses",
        "current_courses",
        "course_credits",
        "test_credits",
        "test_credit_total",
    }
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({"error": "no valid fields to update"}), 400

    db.users.update_one({"email": email}, {"$set": updates}, upsert=True)
    return jsonify({"message": "profile updated"}), 200


@app.post("/user/transcript")
def upload_transcript():
    auth_error = _require_internal_api_token()
    if auth_error:
        return auth_error

    email = request.form.get("email", "").strip().lower()
    file = request.files.get("transcript")

    if not email:
        return jsonify({"error": "email required"}), 400
    if not file or not file.filename:
        return jsonify({"error": "no file uploaded"}), 400
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "only PDF files are supported"}), 400

    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file.read()))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        return jsonify({"error": f"could not read PDF: {exc}"}), 422

    if not text.strip():
        return jsonify({"error": "PDF appears to be empty or image-only"}), 422

    from app.services.transcript_parser import parse_transcript
    result = parse_transcript(text)
    completed = result.get("completed", [])
    current = result.get("current", [])
    course_credits = result.get("course_credits", {})
    test_credits = result.get("test_credits", [])
    test_credit_total = result.get("test_credit_total", 0)

    db.users.update_one(
        {"email": email},
        {"$set": {
            "transcript_raw": text,
            "completed_courses": completed,
            "current_courses": current,
            "course_credits": course_credits,
            "test_credits": test_credits,
            "test_credit_total": test_credit_total,
        }},
        upsert=True,
    )
    return jsonify({
        "courses": completed,
        "current_courses": current,
        "count": len(completed),
        "test_credits": test_credits,
        "test_credit_total": test_credit_total,
    }), 200


@app.get("/programs")
def get_programs():
    programs = requirements_service.list_undergraduate_programs()
    response = jsonify(programs)
    response.headers["Cache-Control"] = "public, max-age=300"
    return response


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
