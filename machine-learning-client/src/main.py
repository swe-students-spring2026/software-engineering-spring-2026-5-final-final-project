import os
from flask import Flask, jsonify, request
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.post('/api/get_priority_score')
def get_priority_score():
    data = request.get_json()
    task_description = data.get("task_description")
    task_days_to_complete = data.get("task_days_to_complete")

    days_to_complete_str = str(task_days_to_complete) + " day"
    if(task_days_to_complete != 1):
        days_to_complete_str += "s"

    response = client.chat.completions.create(
        model = "gpt-4o",
        messages = [
            {"role": "system", "content": "You are a task priority manager machine. You accept as input: a description of a task a user needs to complete, and number of days until the task is due. You should ONLY output a single integer ranging from 1 to 10 (inclusive), that encapsulates the priority of the specified task. The user will complete tasks with a higher priority first."},
            {"role": "user", "content": "Task Description: " + task_description + "\n\n\nTask Due: in " + days_to_complete_str}
        ]
    )

    score = int(response.choices[0].message.content)
    return jsonify({"score": score})

app.run(port=os.getenv("ML_CLIENT_PORT"))
