import os
import pymongo
from datetime import datetime, timezone
from dotenv import load_dotenv

def seed_database():
    print("Connecting to MongoDB...")
    load_dotenv("web-app/.env")
    # Use environment variable or fallback to localhost mapping if running outside docker
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    client = pymongo.MongoClient(mongo_uri)
    
    db_name = os.getenv("MONGO_DB_NAME", "moodmusic")
    db = client[db_name]
    
    print(f"Connected to database: {db_name}")
    
    # 1. Seed dummy sessions
    sessions_col = db["sessions"]
    sessions_col.delete_many({}) # Clear existing for a fresh seed
    
    dummy_sessions = [
        {
            "user_id": "seed_user_1",
            "mood": "feeling calm and a bit nostalgic today...",
            "mood_label": "chill",
            "weather": {"description": "Clear sky", "temp": 72},
            "audio_profile": {"energy": 35, "valence": 60},
            "tracks": [{"id": "1", "name": "Chill Track 1"}, {"id": "2", "name": "Chill Track 2"}],
            "created_at": datetime.now(timezone.utc)
        },
        {
            "user_id": "seed_user_1",
            "mood": "super energetic and ready to work out!",
            "mood_label": "energized",
            "weather": {"description": "Sunny", "temp": 85},
            "audio_profile": {"energy": 90, "valence": 65},
            "tracks": [{"id": "3", "name": "Pump Track 1"}],
            "created_at": datetime.now(timezone.utc)
        }
    ]
    
    result = sessions_col.insert_many(dummy_sessions)
    print(f"Inserted {len(result.inserted_ids)} session records.")

    # 2. Seed dummy playlists
    playlists_col = db["playlists"]
    playlists_col.delete_many({})
    
    dummy_playlists = [
        {
            "user_id": "seed_user_1",
            "tracks": ["1", "2"],
            "created_at": datetime.now(timezone.utc)
        }
    ]
    
    p_result = playlists_col.insert_many(dummy_playlists)
    print(f"Inserted {len(p_result.inserted_ids)} playlist records.")
    
    print("Database seeding complete!")

if __name__ == "__main__":
    seed_database()
