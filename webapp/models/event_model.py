from datetime import datetime


def create_event(data, host_id, image_url=None):
    return {
        "title": data["title"],
        "description": data.get("description", ""),

        "date": data["date"],
        "time": data["time"],
        "location": data.get("location", ""),

        "host_id": host_id,
        "capacity": int(data["capacity"]),

        "tags": data.get("tags", []),
        "image_url": image_url,

        "attendees": [host_id],  # host automatically joins

        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }