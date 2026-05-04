from flask import Blueprint, request, jsonify, redirect, url_for, render_template
from flask_login import current_user, login_required
from bson.objectid import ObjectId
from bson.errors import InvalidId
from datetime import datetime, timezone, timedelta

tasks_bp = Blueprint("tasks", __name__)

def to_object_id(task_id):
    try:
        return ObjectId(task_id)
    except (InvalidId, TypeError):
        return None
    
def parse_yyyy_mm_dd_to_utc(date_str):
    if not date_str:
        return None
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.replace(tzinfo=timezone.utc)

def frequency_to_repeat(freq):
    if not freq or freq == "none":
        return (False, None, None)

    mapping = {
        "hourly": (True, 1, "hours"),
        "daily": (True, 1, "days"),
        "weekly": (True, 1, "weeks"), # can add more
    }
    return mapping.get(freq, (False, None, None))

@tasks_bp.post("/tasks/<task_id>/update")
@login_required
def update_task(task_id):
    task_oid = to_object_id(task_id)
    if task_oid is None:
        return jsonify({"error": "Invalid task id"}), 400
    
    user_id = current_user.id
    title = request.form.get("title")
    date_str = request.form.get("date")
    freq = request.form.get("reminder_frequency")

    update = {}

    if title is not None: 
        update["title"] = title
    if hasattr(current_user, "email") and current_user.email:
        update["user_email"] = current_user.email
    if date_str: 
        next_reminder_at = parse_yyyy_mm_dd_to_utc(date_str)
    reminder_repeat, repeat_every, repeat_unit = frequency_to_repeat(freq)

    if freq is not None:
        if freq == "none":
            update["reminder_enabled"] = False
            update["reminder_repeat"] = False
            update["repeat_every"] = None
            update["repeat_unit"] = None
            update["next_reminder_at"] = None
        else:
            update["reminder_enabled"] = next_reminder_at is not None
            update["reminder_repeat"] = reminder_repeat
            update["repeat_every"] = repeat_every
            update["repeat_unit"] = repeat_unit
            update["next_reminder_at"] = next_reminder_at

    result = tasks_bp.db.tasks.update_one(
        {"_id": task_oid, "user_id": user_id},
        {"$set": update},
    )

    if result.matched_count == 0:
        return jsonify({"error": "Task not found"}), 404

    return redirect(url_for("tasks.show_tasks"))

@tasks_bp.post("/tasks/<task_id>/delete")
@login_required
def delete_task(task_id):
    task_oid = to_object_id(task_id)
    if task_oid is None:
        return jsonify({"error": "Invalid task id"}), 400
    
    user_id = current_user.id 

    result = tasks_bp.db.tasks.delete_one({
        "_id": task_oid,
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