from flask import Flask, render_template, redirect, request
import json
from datetime import datetime

app = Flask(__name__)

overdue = []
due_soon = []
upcoming = []

task_id_counter = 0


@app.route('/')
def index():
    return render_template('index.html', overdue=overdue, due_soon=due_soon, upcoming=upcoming)

@app.route('/submit_new_task', methods=['POST'])
def submit_new_task():
    global task_id_counter

    form_data = request.json

    # fields needed for detail/edit pages
    # temporary data
    form_data['id'] = task_id_counter
    task_id_counter += 1
    form_data['due_date'] = form_data.get('due_date') or form_data.get('date')
    form_data['completed'] = False
    form_data['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    form_data['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # ML placeholder
    form_data['estimated_hours'] = 3
    form_data['difficulty'] = 3
    form_data['priority'] = 'medium'

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

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/api/auth/login', methods=['POST'])
def login():
    return redirect('/')

@app.route('/api/auth/register', methods=['POST'])
def register():
    return redirect('/login') 

def find_task(task_id):
    all_tasks = overdue + due_soon + upcoming
    return next((task for task in all_tasks if task['id'] == task_id), None)

# detail page
@app.route('/task/<int:task_id>')
def task_detail(task_id):
    task = find_task(task_id)
    if task is None:
        return redirect('/')

    return render_template('detail.html', task=task)


@app.route('/task/<int:task_id>/edit', methods=['GET', 'POST'])
def edit_task(task_id):
    task = find_task(task_id)
    if task is None:
        return redirect('/')
    
    if request.method == 'POST':
        task['title'] = request.form.get('title')
        task['course'] = request.form.get('course')
        task['description'] = request.form.get('description')
        task['due_date'] = request.form.get('due_date')
        task['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return redirect(f'/task/{task_id}')
    
    return render_template('edit.html', task=task)



if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)