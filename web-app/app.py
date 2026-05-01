from flask import Flask, render_template, redirect, request
import logging
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import json
import os
import requests
from datetime import datetime
from bson.objectid import ObjectId
import pymongo
from config import Config
from mongo_wrapper import MongoWrapper
import requests

mongo = MongoWrapper()
ML_SERVICE_URL = "http://ml-client:5002/analyze"
app = Flask(__name__)
logger = logging.getLogger(__name__)
app.secret_key = 'lacewing squad'

overdue = []
due_soon = []
upcoming = []
completed = []

task_id_counter = 0

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

class User(UserMixin):
    pass

@login_manager.user_loader
def user_loader(user_email):
    user_doc = mongo.db.users.find_one({"user_email": user_email})
    if not user_doc:
        return None
    user = User()
    user.id = user_email
    return user

@login_manager.request_loader
def request_loader(request):
    user_email = request.form.get('username')
    if not user_email:
        return None
    user_doc = mongo.db.users.find_one({"user_email": user_email})
    if not user_doc:
        return None
    user = User()
    user.id = user_email
    return user

def add_id(tasks):
    for task in tasks:
        task['id'] = str(task['_id'])
    return tasks

@app.route('/')
@login_required
def index():
    user = current_user.id

    overdue = add_id(mongo.get_assignments_by_status(user, "overdue"))
    due_soon = add_id(mongo.get_assignments_by_status(user, "due_soon"))
    upcoming = add_id(mongo.get_assignments_by_status(user, "upcoming"))
    completed = add_id(mongo.get_assignments_by_status(user, "completed"))

    return render_template(
        'index.html',
        overdue=overdue,
        due_soon=due_soon,
        upcoming=upcoming,
        completed=completed
    )

@app.route('/submit_new_task', methods=['POST'])
@login_required
def submit_new_task():
    data = request.json

    try:
        ml_response = requests.post(ML_SERVICE_URL, json={
            "title": data.get("title"),
            "course": data.get("course"),
            "description": data.get("description"),
            "due_date": data.get("date")
        })
        ml_data = ml_response.json()

        mongo.add_assignment(
            user_email=current_user.id,
            title=data.get("title"),
            course=data.get("course"),
            description=data.get("description"),
            due_date=datetime.strptime(data.get("date"), "%Y-%m-%d"),
            estimated_hours=ml_data.get("estimated_hours"),
            difficulty=ml_data.get("difficulty"),
            priority=ml_data.get("priority"),
            status="upcoming"
        )
    except Exception as e:
        logger.exception("ML service request failed: %s", e)
        return json.dumps({'status': 'error', 'message': 'Failed to analyze assignment'})

    return json.dumps({"status": "success"})

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/api/auth/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    user_doc = mongo.db.users.find_one({"user_email": username})
    if not user_doc or user_doc['password'] != password:
        return """<div>wrong username or password</div>
                <a href="/login"> go back to login </a>"""

    user = User()
    user.id = username
    login_user(user)
    return redirect('/')

@app.route('/api/auth/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')

    if mongo.db.users.find_one({"user_email": username}):
        return """<div>username already exists</div>
                <a href="/login"> go to login </a>"""

    mongo.db.users.insert_one({"user_email": username, "password": password})
    return redirect('/login')

def find_task(task_id):
    all_tasks = overdue + due_soon + upcoming + completed
    return next((task for task in all_tasks if task['id'] == task_id), None)

# detail page
@app.route('/task/<task_id>')
def task_detail(task_id):
    task = find_task(task_id)
    if task is None:
        return redirect('/')

    return render_template('detail.html', task=task)

@app.route('/task/<task_id>/edit', methods=['GET', 'POST'])
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

@app.route('/complete_task/<task_id>')
def complete_task(task_id):
    task = find_task(task_id)
    if task is None:
        return redirect('/')
    
    if task in overdue:
        overdue.remove(task)
    elif task in due_soon:
        due_soon.remove(task)
    elif task in upcoming:
        upcoming.remove(task)

    task['completed'] = True
    completed.append(task)
    
    return redirect('/')

@app.route('/logout')
def logout():
    logout_user()
    return 'Logged out'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
