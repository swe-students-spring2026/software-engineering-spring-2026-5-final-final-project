from flask import Flask, request, jsonify, render_template, redirect, session
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from bson.objectid import ObjectId




load_dotenv()

app = Flask(__name__)
app.secret_key = "studycast-secret-key"
client = MongoClient(os.getenv("MONGO_URI"))
db = client["studycast"]

@app.route("/")
def home():
    return redirect("/auth")


@app.route("/dashboard")
def dashboard():
    if "user_name" not in session:
        return redirect("/auth")   # 👈 send back to login

    return render_template("dashboard.html")


@app.route("/todos")
def todos_page():
    todos = list(db.todos.find())

    today_todos = []
    long_term_todos = []

    for todo in todos:
        todo["_id"] = str(todo["_id"])

        if todo.get("type") == "today":
            today_todos.append(todo)
        else:
            long_term_todos.append(todo)

    return render_template(
        "todos.html",
        today_todos=today_todos,
        long_term_todos=long_term_todos
    )


@app.route("/add-todo", methods=["POST"])
def add_todo():
    task = request.form.get("task")
    todo_type = request.form.get("type")

    if task and todo_type:
        db.todos.insert_one({
            "task": task,
            "type": todo_type,
            "completed": False
        })

    return redirect("/todos")


@app.route("/complete-todo/<todo_id>", methods=["POST"])
def complete_todo(todo_id):
    db.todos.update_one(
        {"_id": ObjectId(todo_id)},
        {"$set": {"completed": True}}
    )
    return redirect("/todos")


@app.route("/delete-todo/<todo_id>", methods=["POST"])
def delete_todo(todo_id):
    db.todos.delete_one({"_id": ObjectId(todo_id)})
    return redirect("/todos")
@app.route("/signup", methods=["GET"])
def signup_page():
    return render_template("signup.html")


@app.route("/auth", methods=["GET", "POST"])
def auth():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        action = request.form.get("action")  # login or signup

        if action == "signup":
            existing_user = db.users.find_one({"email": email})

            if existing_user:
                return "User already exists."

            db.users.insert_one({
                "name": name,
                "email": email,
                "password": password
            })

            session["user_name"] = name
            return redirect("/dashboard")

        elif action == "signin":
            user = db.users.find_one({
                "email": email,
                "password": password
            })

            if user:
                session["user_name"] = user["name"]
                return redirect("/dashboard")

            return "Invalid login."

    return render_template("auth.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/auth")








if __name__ == "__main__":
    app.run(debug=True, port=5000)