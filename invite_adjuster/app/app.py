from flask import Flask, jsonify
from pymongo import MongoClient
from bson import ObjectId
import os

app = Flask(__name__)

def get_db():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")
    mongo_dbname = os.getenv("MONGO_DBNAME", "flakemate")
    client = MongoClient(mongo_uri)
    return client[mongo_dbname]

@app.route("/")
def home():
    return jsonify({"message": "invite-adjuster is running"})

@app.route("/lateness_penalty/<user_id>")
def lateness_penalty(user_id):
    db = get_db()
    users = db["users"]
    user = users.find_one({"_id": ObjectId(user_id)})
    if not user or "lateness" not in user or not user["lateness"]:
        return jsonify({"lateness_penalty": None, "message": "No lateness data"})
    lateness_list = user["lateness"][-5:]  # last 5 entries
    avg_penalty = sum(lateness_list) / len(lateness_list)
    return jsonify({"lateness_penalty": avg_penalty, "num_events": len(lateness_list)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)