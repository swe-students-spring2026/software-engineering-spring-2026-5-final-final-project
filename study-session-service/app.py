import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from bson.objectid import ObjectId
from pymongo import MongoClient

from detector import classify_distraction, score_distraction


load_dotenv()

app = Flask(__name__)
client = MongoClient(os.getenv("MONGO_URI", "mongodb://mongodb:27017/"))
db = client[os.getenv("MONGO_DB", "studycast")]


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "study-session-service"})


@app.get("/")
def index():
    return health()


@app.post("/sessions")
def create_session():
    payload = request.get_json(silent=True) or {}
    session = {
        "user": payload.get("user", "anonymous"),
        "started_at": datetime.now(timezone.utc),
        "ended_at": None,
        "events": [],
    }
    result = db.study_sessions.insert_one(session)
    return jsonify({"session_id": str(result.inserted_id)}), 201


@app.post("/sessions/<session_id>/end")
def end_session(session_id):
    payload = request.get_json(silent=True) or {}
    distraction_count = int(payload.get("distraction_count", 0))
    db.study_sessions.update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {
            "ended_at": datetime.now(timezone.utc),
            "distraction_count": distraction_count,
        }},
    )
    return jsonify({"distraction_count": distraction_count, "status": "ended"})


@app.post("/detect")
def detect():
    payload = request.get_json(silent=True) or {}
    score = score_distraction(
        face_present=payload.get("face_present", True),
        looking_away=payload.get("looking_away", False),
        phone_visible=payload.get("phone_visible", False),
    )
    return jsonify({"score": score, "status": classify_distraction(score)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
