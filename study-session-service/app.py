import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from pymongo import MongoClient

from detector import classify_distraction, score_distraction


load_dotenv()

app = Flask(__name__)
client = MongoClient(os.getenv("MONGO_URI", "mongodb://mongodb:27017/"))
db = client[os.getenv("MONGO_DB", "studycast")]


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "study-session-service"})


@app.post("/sessions")
def create_session():
    session = {
        "user": request.json.get("user", "anonymous"),
        "started_at": datetime.now(timezone.utc),
        "ended_at": None,
        "events": [],
    }
    result = db.study_sessions.insert_one(session)
    return jsonify({"session_id": str(result.inserted_id)}), 201


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
