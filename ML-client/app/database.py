from datetime import datetime, timezone
from bson import ObjectId
from pymongo import MongoClient
from config import settings

_client = MongoClient(settings.mongo_uri)
_db = _client["moodmusic"]

sessions_col = _db["sessions"]
feedback_col = _db["feedback"]
playlists_col = _db["playlists"]


def save_session(
    user_id: str | None,
    mood: str,
    weather: dict,
    profile: dict,
    tracks: list[dict],
) -> str:
    """Persist a recommendation session and return its string ID."""
    doc = {
        "user_id": user_id,
        "mood": mood,
        "weather": weather,
        "audio_profile": profile,
        "tracks": tracks,
        "created_at": datetime.now(timezone.utc),
    }
    result = sessions_col.insert_one(doc)
    return str(result.inserted_id)


def save_feedback(session_id: str, track_uri: str, rating: int) -> bool:
    """Store a user rating (1–5) for a specific track in a session."""
    doc = {
        "session_id": session_id,
        "track_uri": track_uri,
        "rating": rating,
        "created_at": datetime.now(timezone.utc),
    }
    result = feedback_col.insert_one(doc)
    return result.acknowledged


def get_session(session_id: str) -> dict | None:
    """Retrieve a session by ID."""
    try:
        return sessions_col.find_one({"_id": ObjectId(session_id)})
    except Exception:
        return None
