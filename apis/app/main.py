import io
import math
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from pymongo import MongoClient
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from apis.app.services.requirements_service import RequirementsService
    from apis.app.services.professor_ratings import (
        build_professor_profile,
        enrich_classes_with_professor_ratings,
        search_professors,
    )
except ModuleNotFoundError:
    from app.services.requirements_service import RequirementsService
    from app.services.professor_ratings import (
        build_professor_profile,
        enrich_classes_with_professor_ratings,
        search_professors,
    )

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

from app.ai.tools import init_tools  # noqa: E402
init_tools(db)


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "apis"})


TERM_CODES: dict[str, str] = {
    "1268": "Fall 2026",
    "1266": "Summer 2026",
    "1264": "Spring 2026",
}


@app.get("/classes")
def get_classes():
    term      = request.args.get("term")
    q         = request.args.get("q")
    school    = request.args.get("school")
    component = request.args.get("component")
    status    = request.args.get("status")
    page      = max(1, request.args.get("page", default=1, type=int))
    page_size = 20

    query: dict = {}

    if term:
        term_name = TERM_CODES.get(term, term)
        query["term"] = term_name
    if school:
        query["school"] = {"$regex": school, "$options": "i"}
    if component:
        query["component"] = {"$regex": component, "$options": "i"}
    if status == "open":
        query["status"] = {"$regex": r"^open$", "$options": "i"}
    elif status == "closed":
        query["status"] = {"$regex": r"^closed$", "$options": "i"}
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

    all_codes = sorted(db.classes.distinct("code", query))
    total_courses = len(all_codes)
    total_pages = math.ceil(total_courses / page_size) if total_courses > 0 else 1
    page_codes = all_codes[(page - 1) * page_size : page * page_size]

    classes = list(db.classes.find({**query, "code": {"$in": page_codes}}, {"_id": 0, "source": 0}))
    classes = enrich_classes_with_professor_ratings(classes)
    return jsonify({
        "classes": classes,
        "total_courses": total_courses,
        "page": page,
        "total_pages": total_pages,
    })


@app.get("/classes/schools")
def get_schools():
    schools = db.classes.distinct("school")
    return jsonify(sorted(s for s in schools if s))


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
    email = request.args.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "email required"}), 400
    user = db.users.find_one({"email": email}, {"_id": 0, "password": 0})
    if not user:
        return jsonify({"error": "user not found"}), 404
    return jsonify(user)


@app.put("/user/profile")
def update_profile():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "email required"}), 400

    allowed = {"name", "major", "graduation_year", "student_id", "completed_courses"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({"error": "no valid fields to update"}), 400

    db.users.update_one({"email": email}, {"$set": updates}, upsert=True)
    return jsonify({"message": "profile updated"}), 200


@app.post("/user/transcript")
def upload_transcript():
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

    db.users.update_one(
        {"email": email},
        {"$set": {"transcript_raw": text}},
        upsert=True,
    )

    from app.ai.service import parse_transcript
    result = parse_transcript(text)
    completed = result.get("completed", [])
    current = result.get("current", [])

    db.users.update_one(
        {"email": email},
        {"$set": {"completed_courses": completed, "current_courses": current}},
        upsert=True,
    )
    return jsonify({"courses": completed, "current_courses": current, "count": len(completed)}), 200


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
