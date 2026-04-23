import os

from flask import Flask, jsonify

from app.routes.chat import chat_bp

app = Flask(__name__)
app.register_blueprint(chat_bp)


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "apis"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ["API_INTERNAL_PORT"]))
