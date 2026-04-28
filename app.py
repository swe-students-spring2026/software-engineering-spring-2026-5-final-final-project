from flask import Flask, request, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

client = MongoClient(os.getenv("MONGO_URI"))
db = client["studycast"]

@app.route("/")
def home():
    return redirect("/dashboard")


@app.route("/dashboard")
def dashboard():
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)