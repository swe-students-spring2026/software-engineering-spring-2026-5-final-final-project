from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.database import get_likes_collection, get_users_collection
from app.services.matching import compute_score

router = APIRouter(prefix="/api", tags=["feed"])

_PAGE_SIZE = 10


@router.get("/feed")
async def get_feed(page: int = 0, current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_spotify_connected"):
        raise HTTPException(status_code=403, detail="spotify_required")

    user_id = str(current_user["_id"])

    likes_col = get_likes_collection()
    liked_ids: set[str] = set()
    async for doc in likes_col.find({"from_user_id": user_id}, {"to_user_id": 1}):
        liked_ids.add(doc["to_user_id"])

    exclude_oids = [current_user["_id"]] + [ObjectId(uid) for uid in liked_ids]
    query: dict = {
        "_id": {"$nin": exclude_oids},
        "is_spotify_connected": True,
    }

    if current_user.get("gender_preference") and current_user["gender_preference"] != "any":
        query["gender"] = current_user["gender_preference"]

    age_pref = current_user.get("age_range_preference")
    if age_pref:
        query["age"] = {"$gte": age_pref["min"], "$lte": age_pref["max"]}

    if current_user.get("city"):
        query["city"] = current_user["city"]

    users = get_users_collection()
    candidates = []
    async for user in users.find(query):
        sp = user.get("spotify") or {}
        candidates.append({
            "user_id": str(user["_id"]),
            "display_name": user["display_name"],
            "age": user["age"],
            "city": user["city"],
            "bio": user.get("bio"),
            "top_genres": sp.get("top_genres") or [],
            "top_artists": sp.get("top_artists") or [],
            "match_score": compute_score(current_user, user),
            "photo_url": None,
        })

    candidates.sort(key=lambda x: x["match_score"], reverse=True)

    start = page * _PAGE_SIZE
    end = start + _PAGE_SIZE
    return {
        "profiles": candidates[start:end],
        "page": page,
        "has_more": end < len(candidates),
    }
