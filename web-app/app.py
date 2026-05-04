import os

import requests
from flask import Flask, render_template, request

app = Flask(__name__)

ML_API_URL = os.environ.get("ML_API_URL", "http://localhost:8000")


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    user_query = request.form.get("query", "").strip()

    if not user_query:
        return render_template("index.html", error="Please enter a search query.")

    try:
        response = requests.post(
            f"{ML_API_URL}/recommend",
            json={"query": user_query},
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()

        return render_template(
            "results.html",
            user_query=user_query,
            reversed_attribute=data.get("reversed_attribute", ""),
            place_type=data.get("place_type", ""),
            results=data.get("results", []),
            from_cache=False,
        )
    except Exception as e:
        return render_template(
            "index.html",
            error=f"Something went wrong while processing your search: {e}",
        )


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
