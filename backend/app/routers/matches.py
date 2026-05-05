from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.database import get_matches_collection, get_users_collection

router = APIRouter(prefix="/api/matches", tags=["matches"])


async def _build_match_entry(match: dict, current_user_id: str, users) -> dict:
    other_id = next(uid for uid in match["user_ids"] if uid != current_user_id)
    try:
        other = await users.find_one({"_id": ObjectId(other_id)})
    except Exception:
        other = None
    return {
        "match_id": str(match["_id"]),
        "other_user": {
            "user_id": other_id,
            "display_name": other["display_name"] if other else "Unknown",
            "age": other["age"] if other else 0,
            "city": other["city"] if other else "",
            "top_genres": ((other.get("spotify") or {}).get("top_genres") or []) if other else [],
            "photo_url": other.get("photo_url") if other else None,
        },
        "created_at": match["created_at"],
        "is_new": current_user_id not in (match.get("seen_by") or []),
    }


@router.get("")
async def get_matches(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    matches_col = get_matches_collection()
    users = get_users_collection()

    result = []
    async for match in matches_col.find({"user_ids": user_id}):
        result.append(await _build_match_entry(match, user_id, users))

    result.sort(key=lambda x: x["created_at"], reverse=True)
    return {"matches": result}


@router.patch("/{match_id}/seen")
async def mark_seen(match_id: str, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    matches_col = get_matches_collection()

    try:
        oid = ObjectId(match_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Match not found")

    match = await matches_col.find_one({"_id": oid, "user_ids": user_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    await matches_col.update_one({"_id": oid}, {"$addToSet": {"seen_by": user_id}})
    return {"detail": "Match marked as seen"}
