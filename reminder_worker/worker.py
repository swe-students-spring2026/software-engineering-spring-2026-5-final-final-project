import time
from reminder_service import process_due_reminders
from db import get_tasks_collection
from email_service import send_task_reminder

def run_worker():
    tasks_collection = get_tasks_collection()
    print("Worker started ")

    while True:
        try:
            count = process_due_reminders(
                tasks_collection,
                send_task_reminder
            )
            print(f"Processed {count} reminders ")
        except Exception as e:
            print("Worker error: ", e)
        time.sleep(60) 
#waiting 60 seconds
if __name__ == "__main__":
    run_worker()
