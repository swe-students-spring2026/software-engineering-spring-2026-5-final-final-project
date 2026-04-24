import os

import requests
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

API_URL = os.environ.get("API_URL", "http://backend:8000")


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/classes")
def classes():
    params = dict(request.args)
    resp = requests.get(f"{API_URL}/classes", params=params)
    return jsonify(resp.json()), resp.status_code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ["FRONTEND_INTERNAL_PORT"]))
