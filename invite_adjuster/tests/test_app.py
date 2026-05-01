import requests
from pymongo import MongoClient
from bson import ObjectId
import time

MONGO_URI = "mongodb://mongodb:27017/"
DB_NAME = "flakemate"
USER_ID = "69f4a33044e301353c9f2c1c"
LATENESS_VALUES = [15, -5, 5, 0, -3, 18]

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
users = db["users"]

# Ensure user exists
users.update_one(
    {"_id": ObjectId(USER_ID)},
    {"$set": {"lateness": LATENESS_VALUES}},
    upsert=True
)

print(f"Set lateness for user {USER_ID} to {LATENESS_VALUES}")
print("All users in DB:", list(users.find()))

time.sleep(1) 

url = f"http://invite-adjuster:5000/lateness_penalty/{USER_ID}"
response = requests.get(url)
print("API response:", response.json())

expected = sum(LATENESS_VALUES[-5:]) / len(LATENESS_VALUES[-5:])
print(f"Expected lateness_penalty: {expected} (from last 5 values: {LATENESS_VALUES[-5:]})")