def test_lateness_penalty():
    import requests
    from pymongo import MongoClient
    from bson import ObjectId
    import time
    import os

    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    DB_NAME = "flakemate"
    USER_ID = "69f4a33044e301353c9f2c1c"
    LATENESS_VALUES = [15, -5, 5, 0, -3, 18]

    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    users = db["users"]

    users.update_one(
        {"_id": ObjectId(USER_ID)},
        {"$set": {"lateness": LATENESS_VALUES}},
        upsert=True
    )

    time.sleep(1)

    url = f"http://localhost:5000/lateness_penalty/{USER_ID}"
    response = requests.get(url)
    data = response.json()

    expected = sum(LATENESS_VALUES[-5:]) / len(LATENESS_VALUES[-5:])
    assert data["lateness_penalty"] == expected