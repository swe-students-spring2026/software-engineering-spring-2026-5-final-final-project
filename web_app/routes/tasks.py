from flask import Blueprint, request, jsonify, redirect, url_for, render_template
from flask_login import current_user, login_required
from bson.objectid import ObjectId
from bson.errors import InvalidId
from datetime import datetime, timezone

tasks_bp = Blueprint("tasks", __name__)


def to_object_id(task_id):
    try:
        return ObjectId(task_id)
    except (InvalidId, TypeError):
        return None


def parse_datetime_local_to_utc(datetime_str):
    if not datetime_str:
        return None

    dt = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M")
    return dt.replace(tzinfo=timezone.utc)


@tasks_bp.post("/tasks/<task_id>/delete")
@login_required
def delete_task(task_id):
    task_oid = to_object_id(task_id)
    if task_oid is None:
        return jsonify({"error": "Invalid task id"}), 400

    result = tasks_bp.db.tasks.delete_one({
        "_id": task_oid,
        "user_id": current_user.id
    })

    if result.deleted_count == 0:
        return jsonify({"error": "Task not found"}), 404

    return redirect(url_for("tasks.show_tasks"))


@tasks_bp.route("/tasks/create", methods=["GET", "POST"])
@login_required
def create_task():
    if request.method == "POST":
        title = request.form.get("title")
        next_reminder_at = parse_datetime_local_to_utc(
            request.form.get("next_reminder_at")
        )

        reminder_enabled = request.form.get("reminder_enabled") == "on"
        reminder_repeat = request.form.get("reminder_repeat") == "on"

        repeat_every_raw = request.form.get("repeat_every")
        repeat_every = int(repeat_every_raw) if repeat_every_raw else None
        repeat_unit = request.form.get("repeat_unit") if reminder_repeat else None

        tasks_bp.db.tasks.insert_one({
            "user_id": current_user.id,
            "user_email": current_user.email,
            "title": title,
            "completed": False,
            "reminder_enabled": reminder_enabled,
            "next_reminder_at": next_reminder_at,
            "reminder_repeat": reminder_repeat,
            "repeat_every": repeat_every if reminder_repeat else None,
            "repeat_unit": repeat_unit,
        })

        return redirect(url_for("tasks.show_tasks"))

    return render_template("create_task.html")


@tasks_bp.route("/", methods=["GET"])
@login_required
def show_tasks():
    results = tasks_bp.db.tasks.find({"user_id": current_user.id})
    return render_template("index.html", tasks=results)