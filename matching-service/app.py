"""Simple matching service API."""

import os
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.post("/match")
def match():
    """Placeholder matching endpoint."""
    payload = request.get_json(silent=True) or {}
    return jsonify({"matched": True, "input": payload})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5001"))
    app.run(host="0.0.0.0", port=port)
