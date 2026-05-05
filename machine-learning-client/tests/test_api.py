import os
import requests

def get_priority_score(task_description, task_days_to_complete):
    try:
        response = requests.post(
            "http://localhost:" + os.getenv("ML_CLIENT_PORT") + "/api/get_priority_score",
            json={"task_description": task_description, "task_days_to_complete": task_days_to_complete}
            # timeout=ML_CLIENT_TIMEOUT_SECONDS,
        )
    except requests.RequestException:
        return "unable to reach ml service", 502

    if(response.status_code != 200):
        return f"ml service error ({response.status_code})", 502

    try:
        payload = response.json()
        return payload
    except ValueError:
        return "invalid response from ml service", 502

print(get_priority_score("finish geometry homework, pretty easy, I can do it in 5 minutes", 10))
print(get_priority_score("huge physics project that requires at least 2 hours of research tests and a 20 page paper. I haven't started yet", 3))