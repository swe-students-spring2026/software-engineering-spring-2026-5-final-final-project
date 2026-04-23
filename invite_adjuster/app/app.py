# this is a test file for invite adjuster to show it is an independent subsystem
# can be deleted later
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"message": "invite-adjuster is running"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)