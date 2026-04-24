import os

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

API_URL = os.environ.get("API_URL", "http://backend:8000")


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/classes")
def proxy_classes():
    params = dict(request.args)
    resp = requests.get(f"{API_URL}/classes", params=params)
    return jsonify(resp.json()), resp.status_code


@app.get("/api/schools")
def proxy_schools():
    resp = requests.get(f"{API_URL}/schools")
    return jsonify(resp.json()), resp.status_code


@app.get("/api/campuses")
def proxy_campuses():
    resp = requests.get(f"{API_URL}/campuses")
    return jsonify(resp.json()), resp.status_code


@app.post("/api/chat")
def proxy_chat():
    payload = request.get_json(silent=True) or {}
    resp = requests.post(f"{API_URL}/chat", json=payload)
    return jsonify(resp.json()), resp.status_code


if __name__ == "__main__":
    port = int(os.environ.get("PORT") or os.environ.get("FRONTEND_INTERNAL_PORT", "3000"))
    app.run(host="0.0.0.0", port=port)
