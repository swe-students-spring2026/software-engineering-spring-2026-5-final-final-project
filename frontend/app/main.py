import os

import requests
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

API_URL = os.environ.get("API_URL", "http://backend:8000")


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/schedule")
def schedule():
    return render_template("schedule.html")


@app.get("/api/classes")
def classes():
    resp = requests.get(f"{API_URL}/classes", params=dict(request.args))
    return jsonify(resp.json()), resp.status_code


@app.post("/api/chat")
def chat():
    resp = requests.post(f"{API_URL}/chat", json=request.get_json(silent=True) or {})
    return jsonify(resp.json()), resp.status_code


@app.get("/api/schools")
def schools():
    resp = requests.get(f"{API_URL}/classes/schools")
    return jsonify(resp.json()), resp.status_code


@app.get("/api/campuses")
def campuses():
    resp = requests.get(f"{API_URL}/classes/campuses")
    return jsonify(resp.json()), resp.status_code


@app.get("/api/schools")
def schools():
    resp = requests.get(f"{API_URL}/schools")
    return jsonify(resp.json()), resp.status_code


@app.get("/api/campuses")
def campuses():
    resp = requests.get(f"{API_URL}/campuses")
    return jsonify(resp.json()), resp.status_code


@app.post("/api/chat")
def chat():
    resp = requests.post(f"{API_URL}/chat", json=request.get_json())
    return jsonify(resp.json()), resp.status_code


if __name__ == "__main__":
    port = int(os.environ.get("PORT") or os.environ.get("FRONTEND_INTERNAL_PORT", "3000"))
    app.run(host="0.0.0.0", port=port)
