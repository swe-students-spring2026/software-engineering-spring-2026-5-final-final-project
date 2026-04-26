from flask import Flask, request
from analyzer import analyze_feedback

app = Flask(__name__)

@app.route("/analyze", methods=["POST"])
def analyze():
    feedback = request.form.get("feedback", "")

    if not isinstance(feedback, str) or not feedback.strip():
        return {"error": "'feedback' must be a non-empty string"}, 400

    result = analyze_feedback(feedback)
    return result


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
