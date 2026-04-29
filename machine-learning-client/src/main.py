import os
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.post('/api/get_priority_score')
def get_priority_score():
    data = request.get_json()
    # TODO: impl
    score = 0
    return jsonify({"score": score})

app.run(port=os.getenv("ML_CLIENT_PORT"))
