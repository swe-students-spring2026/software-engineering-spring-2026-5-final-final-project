from datetime import datetime, timezone, timedelta


def find_due_reminders(task_collection):
    now = datetime.now(timezone.utc)

    return list(
        task_collection.find(
            {
                "completed": False,
                "reminder_enabled": True,
                "next_reminder_at": {"$lte": now},
            }
        )
    )


def calculate_next_reminder(task):
    repeat_every = task.get("repeat_every")
    repeat_unit = task.get("repeat_unit")

    if not repeat_every or not repeat_unit:
        return None

    if repeat_unit == "minutes":
        return datetime.now(timezone.utc) + timedelta(minutes=repeat_every)

    if repeat_unit == "hours":
        return datetime.now(timezone.utc) + timedelta(hours=repeat_every)

    if repeat_unit == "days":
        return datetime.now(timezone.utc) + timedelta(days=repeat_every)

    if repeat_unit == "weeks":
        return datetime.now(timezone.utc) + timedelta(weeks=repeat_every)

    return None


def process_due_reminders(task_collection, send_func):
    due_tasks = find_due_reminders(task_collection)

    for task in due_tasks:
        send_func(
            task.get("user_email", "example@example.com"),
            task.get("title", "Untitled Task"),
            str(task.get("next_reminder_at", "unknown time")),
        )

        if task.get("reminder_repeat") is True:
            next_time = calculate_next_reminder(task)

            task_collection.update_one(
                {"_id": task["_id"]},
                {
                    "$set": {
                        "last_reminder_sent_at": datetime.now(timezone.utc),
                        "next_reminder_at": next_time,
                    }
                },
            )

        else:
            task_collection.update_one(
                {"_id": task["_id"]},
                {
                    "$set": {
                        "last_reminder_sent_at": datetime.now(timezone.utc),
                        "reminder_enabled": False,
                    }
                },
            )

    return len(due_tasks)
