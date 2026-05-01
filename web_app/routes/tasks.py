from flask import Blueprint, request, jsonify, redirect, url_for, render_template
from flask_login import current_user, login_required
from bson.objectid import ObjectId
from bson.errors import InvalidId

from datetime import datetime
tasks_bp = Blueprint("tasks", __name__)

def to_object_id(task_id):
    try:
        return ObjectId(task_id)
    except (InvalidId, TypeError):
        return None

@tasks_bp.post("/tasks/<task_id>/update")
@login_required
def update_task(task_id):
    user_id = current_user.id
    title = request.form.get("title")
    date = request.form.get("date")
    freq = request.form.get("reminder_frequency")

    update = {}
    if title is not None: update["title"] = title
    if date: update["date"] = datetime.strptime(date, "%Y-%m-%d")
    if freq is not None: update["reminder_frequency"] = freq

    result = tasks_bp.db.tasks.update_one(
        {"_id": ObjectId(task_id), "user_id": user_id},
        {"$set": update}
    )

    if result.matched_count == 0:
        return jsonify({"error": "Task not found"}), 404

    return redirect(url_for("tasks.show_tasks"))

@tasks_bp.post("/tasks/<task_id>/delete")
@login_required
def delete_task(task_id):
    user_id = current_user.id 

    result = tasks_bp.db.tasks.delete_one({
        "_id": ObjectId(task_id),
        "user_id": user_id
    })

    if result.deleted_count == 0:
        return jsonify({"error": "Task not found"}), 404

    return redirect(url_for("tasks.show_tasks"))

@tasks_bp.route("/tasks/create", methods = ['GET', 'POST'])
@login_required
def create_task():
    if request.method == 'POST':
        user_id = current_user.id
        title = request.form.get("title")
        date = request.form.get("date")
        freq = request.form.get("reminder_frequency")
        task_date = datetime.strptime(date, "%Y-%m-%d") if date else None

        tasks_bp.db.tasks.insert_one({
            "user_id": user_id,
            "title": title,
            "date": task_date,
            "reminder_frequency": freq
        })

        return redirect(url_for("tasks.show_tasks"))
    return render_template("create_task.html")

@tasks_bp.route('/', methods = ['GET'])
@login_required
def show_tasks():
    results = tasks_bp.db.tasks.find({"user_id": current_user.id})
    return render_template("index.html", tasks = results)