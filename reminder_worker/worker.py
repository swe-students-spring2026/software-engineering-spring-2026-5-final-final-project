import time
import traceback
from reminder_service import process_due_reminders
from db import get_tasks_collection
from email_service import send_task_reminder

def run_worker():
    tasks_collection = get_tasks_collection()
    print("Reminder worker started")

    while True:
        try:
            count = process_due_reminders(
                tasks_collection,
                send_task_reminder
            )

            print(f"[OK] Processed {count} reminders")

        except Exception as e:
            print("[WORKER ERROR]")
            print(e)
            traceback.print_exc()
        time.sleep(60)
#wait 60 secs

if __name__ == "__main__":
    run_worker()