import os

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

API_URL = os.environ.get("API_URL", "http://backend:8000")


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/schedule")
def schedule():
    return render_template("schedule.html")


@app.get("/programs")
def programs_page():
    return render_template("programs.html")


@app.get("/api/programs")
def programs():
    resp = requests.get(f"{API_URL}/programs")
    return jsonify(resp.json()), resp.status_code


@app.get("/api/program-requirements")
def program_requirements():
    resp = requests.get(f"{API_URL}/program-requirements", params=dict(request.args))
    return jsonify(resp.json()), resp.status_code


@app.get("/api/classes")
def proxy_classes():
    params = dict(request.args)
    resp = requests.get(f"{API_URL}/classes", params=params)
    return jsonify(resp.json()), resp.status_code


@app.get("/api/schools")
def proxy_schools():
    resp = requests.get(f"{API_URL}/classes/schools")
    return jsonify(resp.json()), resp.status_code


@app.get("/api/campuses")
def proxy_campuses():
    resp = requests.get(f"{API_URL}/classes/campuses")
    return jsonify(resp.json()), resp.status_code


@app.post("/api/chat")
def proxy_chat():
    payload = request.get_json(silent=True) or {}
    resp = requests.post(f"{API_URL}/chat", json=payload)
    return jsonify(resp.json()), resp.status_code


if __name__ == "__main__":
    port = int(os.environ.get("PORT") or os.environ.get("FRONTEND_INTERNAL_PORT", "3000"))
    app.run(host="0.0.0.0", port=port)
