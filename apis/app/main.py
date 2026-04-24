import os

from flask import Flask, jsonify, request
from pymongo import MongoClient

app = Flask(__name__)

client = MongoClient(os.environ["MONGO_URI"])
db = client[os.environ["MONGO_DB_NAME"]]


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "apis"})


@app.get("/classes")
def get_classes():
    term = request.args.get("term")
    query = {"term_code": term} if term else {}
    classes = list(db.classes.find(query, {"_id": 0}))
    return jsonify(classes)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ["API_INTERNAL_PORT"]))
