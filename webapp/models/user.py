from datetime import datetime

def create_user(data):
    return {
        "email": data["email"],
        "password_hash": data["password_hash"],
        "first_name": data["first_name"],
        "last_initial": data["last_name"][0],

        "age": int(data["age"]),
        "neighborhood": data["neighborhood"],
        "pronouns": data.get("pronouns"),

        "drinking_smoking": {
            "drinks": data.get("drinks"),
            "smokes": data.get("smokes"),
        },

        "dietary_restrictions": data.get("dietary_restrictions", []),
        "hobbies": data.get("hobbies", []),
        "interests": data.get("interests", []),

        "created_events": [],
        "joined_events": [],

        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }