from flask import Flask, render_template, redirect, request
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
import json
from datetime import datetime
from bson.objectid import ObjectId
import pymongo
from config import Config
from mongo_wrapper import MongoWrapper

app = Flask(__name__)
app.secret_key = 'lacewing squad'

overdue = []
due_soon = []
upcoming = []
completed = []

task_id_counter = 0

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

users = {} #    REPLACE W MONGODB

class User(UserMixin):
    pass

@login_manager.user_loader
def user_loader(username):
    if username not in users:
        return
    user = User()
    user.id = username
    return user

@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    if username not in users:
        return
    user = User()
    user.id = username
    return user


@app.route('/')
@login_required
def index():
    return render_template('index.html', overdue=overdue, due_soon=due_soon, upcoming=upcoming, completed=completed)

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

    if username not in users or users[username]['password'] != password:
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

    if username in users:
        return """<div>username already exists</div>
                <a href="/login"> go to login </a>"""

    users[username] = {'password': password}
    print(users)
    return redirect('/login')

def find_task(task_id):
    all_tasks = overdue + due_soon + upcoming + completed
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


@app.route('/complete_task/<int:task_id>')
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
    app.run(host='127.0.0.1', port=5000)

    class MongoWrapper:
    def __init__(self):
        config = Config()
        self.db = config.connect_to_db()

    # Add a new assignment into database
    # _id : ObjectID, generated automatically
    # user_email : String, associates assignment with user
    # title : String
    # course : String
    # description : String
    # due_date : datetime
    # estimated_hours : int
    # difficulty : int (1-5)
    # priority : String (low, medium, high)
    # status : String (overdue, due_soon, upcoming, completed)
    # completed : boolean (default false)
    # Returns the id of the newly created assignment as a string
    def add_assignment(
        self,
        user_email,
        title,
        course,
        description,
        due_date,
        estimated_hours,
        difficulty,
        priority,
        status,
        completed=False,
    ):
        doc = {
            "user_email": user_email,
            "title": title,
            "course": course,
            "description": description,
            "due_date": due_date,
            "estimated_hours": estimated_hours,
            "difficulty": difficulty,
            "priority": priority,
            "status": status,
            "completed": completed,
            "created_at": datetime.datetime.now(datetime.timezone.utc),
            "updated_at": datetime.datetime.now(datetime.timezone.utc),
        }

        result = self.db.assignments.insert_one(doc)
        return str(result.inserted_id)

    # Find assignments
    # user_email : String, the user to find assignments for
    # view : string with the value day/week/month
    # date : dateTime , optional, only include if viewing from the past/future, defaults to current
    # course : String, optional, only include if searching for a specific course
    # returns a list of assignment docs due today, this week, or this month/from the provided date
    def view_assignments(self, user_email, view, date=None, course=None):
        if date == None:
            day = datetime.datetime.now(datetime.timezone.utc)
        elif isinstance(date, datetime.datetime):
            day = date

        if view == "day":
            # Set start to beginning of day, end to beginning of next day
            start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + datetime.timedelta(days=1)
        elif view == "week":
            # Set start to beginning of week, end to beginning of next week
            start = day - datetime.timedelta(days=day.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + datetime.timedelta(days=7)
        elif view == "month":
            # Set start to beginning of month, end to beginning of next month, adding 32 days guarantees the end is next month
            start = day.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = (start + datetime.timedelta(days=32)).replace(day=1)

        if course == None:
            assignments = list(
                self.db.assignments.find(
                    {"user-email": user_email, "due_date": {"$gte": start, "$lt": end}}
                )
            )
        else:
            assignments = list(
                self.db.assignments.find(
                    {
                        "user-email": user_email,
                        "course": course,
                        "due_date": {"$gte": start, "$lt": end},
                    }
                )
            )

        return assignments

    # Mark assignment completed by id
    # _id : String, it's converted to ObjectId in the function
    # If sending get_assignment_id, _id possibly is None, in which case returns ValueError
    # Returns nothing on success, ValueError on failure
    def mark_completed(self, _id):
        if _id == None:
            return ValueError("Invalid value for _id parameter")
        elif not ObjectId.is_valid(_id):
            return ValueError("Invalid ObjectID")

        _id = ObjectId(_id)

        self.db.assignments.update_one(
            {"_id": ObjectId(_id)},
            {
                "$set": {
                    "completed": True,
                    "status": "completed",
                    "updated_at": datetime.datetime.now(datetime.timezone.utc),
                }
            },
        )

    # Get list of assignments with provided status, or ValueError if status invalid
    # user_email : String, the user to find assignments for
    # status : String (overdue, due_soon, upcoming, completed)
    # Use for status tracker
    def get_assignments_by_status(self, user_email, status):
        if status not in ["overdue", "due_soon", "upcoming", "completed"]:
            raise ValueError("Invalid value for status parameter")

        assignments = list(
            self.db.assignments.find({"user-email": user_email, "status": status})
        )
        return assignments

    # Get assignment id by title and course
    # user_email : String, the user to find assignment id for
    # Used to send into other methods mostly
    # Return: String id / None if not found
    def get_assignment_id(self, user_email, title, course):
        assignment = self.db.assignments.find_one(
            {"user-email": user_email, "title": title, "course": course}
        )

        if assignment:
            return str(assignment["_id"])
        else:
            return None