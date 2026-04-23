import os

from flask import Flask


app = Flask(__name__)


@app.get("/")
def index():
    return "Frontend container is running."


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ["FRONTEND_INTERNAL_PORT"]))
