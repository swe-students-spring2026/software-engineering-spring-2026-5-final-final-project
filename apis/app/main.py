import os

from flask import Flask, jsonify, request
from pymongo import MongoClient

from app.routes.chat import chat_bp

app = Flask(__name__)
app.register_blueprint(chat_bp)

client = MongoClient(os.environ["MONGO_URI"])
db = client[os.environ["MONGO_DB_NAME"]]


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ["API_INTERNAL_PORT"]))
