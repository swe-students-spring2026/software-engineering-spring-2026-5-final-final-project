from flask import Flask, render_template, jsonify
from pymongo import MongoClient
import os

app = Flask(__name__)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongo:27017/")
client = MongoClient(MONGO_URI)
db = client["webapp"]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    try:
        client.admin.command("ping")
        return jsonify({"status": "ok", "mongo": "connected"})
    except Exception as e:
        return jsonify({"status": "error", "mongo": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
