from flask import Blueprint, request, jsonify, redirect, url_for
from bson.objectid import ObjectId
from bson.errors import InvalidId

tasks_bp = Blueprint("tasks", __name__)

def to_object_id(task_id):
    try:
        return ObjectId(task_id)
    except (InvalidId, TypeError):
        return None

@tasks_bp.post("/tasks/<task_id>/update")
def update_task(task_id):
    user_id = request.args.get("user_id")  # TODO replace placeeholder with real user id when have authentication

    title = request.form.get("title")
    date = request.form.get("date")
    freq = request.form.get("reminder_frequency")

    update = {}
    if title is not None: update["title"] = title
    if date is not None: update["date"] = date
    if freq is not None: update["reminder_frequency"] = freq

    result = tasks_bp.db.tasks.update_one(
        {"_id": ObjectId(task_id), "user_id": user_id},
        {"$set": update}
    )

    if result.matched_count == 0:
        return jsonify({"error": "Task not found"}), 404

    return redirect(url_for("show_tasks"))

@tasks_bp.post("/tasks/<task_id>/delete")
def delete_task(task_id):
    user_id = request.args.get("user_id")  # TODO replace placeeholder with real user id when have authentication

    result = tasks_bp.db.tasks.delete_one({
        "_id": ObjectId(task_id),
        "user_id": user_id
    })

    if result.deleted_count == 0:
        return jsonify({"error": "Task not found"}), 404

    return redirect(url_for("show_tasks"))