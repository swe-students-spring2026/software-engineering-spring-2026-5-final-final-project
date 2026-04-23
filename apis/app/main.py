import os

from flask import Flask, jsonify


app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "apis"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ["API_INTERNAL_PORT"]))
