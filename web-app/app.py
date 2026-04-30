from flask import Flask, render_template, redirect, request
import json

app = Flask(__name__)

overdue = []
due_soon = []
upcoming = []

@app.route('/')
def index():
    return render_template('index.html', overdue=overdue, due_soon=due_soon, upcoming=upcoming)

@app.route('/submit_new_task', methods=['POST'])
def submit_new_task():
    form_data = request.json
    if form_data.get('status') == 'overdue':
        overdue.append(form_data)
    elif form_data.get('status') == 'due_soon':
        due_soon.append(form_data)
    elif form_data.get('status') == 'upcoming':
        upcoming.append(form_data)

    payload = {
        'status': 'success'
    }
    return json.dumps(payload)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)