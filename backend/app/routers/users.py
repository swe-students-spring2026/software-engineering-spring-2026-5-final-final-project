from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.auth import get_current_user
from app.config import get_settings
from app.database import get_matches_collection, get_users_collection
from app.models.schemas import UpdateProfileRequest
from app.routers.auth import _user_to_dict

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me")
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    return _user_to_dict(current_user)


@router.put("/me")
async def update_profile(
    body: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
):
    update: dict = {}
    if body.display_name is not None:
        update["display_name"] = body.display_name
    if body.age is not None:
        update["age"] = body.age
    if body.city is not None:
        update["city"] = body.city
    if body.bio is not None:
        update["bio"] = body.bio
    if body.gender is not None:
        update["gender"] = body.gender
    if body.gender_preference is not None:
        update["gender_preference"] = body.gender_preference
    if body.age_range_preference is not None:
        update["age_range_preference"] = body.age_range_preference.model_dump()
    if body.contact_info is not None:
        update["contact_info"] = body.contact_info.model_dump()
    update["updated_at"] = datetime.now(timezone.utc)

    users = get_users_collection()
    await users.update_one({"_id": current_user["_id"]}, {"$set": update})
    updated = await users.find_one({"_id": current_user["_id"]})
    return _user_to_dict(updated)


@router.post("/me/photo")
async def upload_photo(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=422, detail="Unsupported image format")

    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="File too large (max 5MB)")

    s = get_settings()
    if not s.cloudinary_cloud_name:
        raise HTTPException(status_code=503, detail="Photo upload not configured")

    import cloudinary
    import cloudinary.uploader

    cloudinary.config(
        cloud_name=s.cloudinary_cloud_name,
        api_key=s.cloudinary_api_key,
        api_secret=s.cloudinary_api_secret,
    )
    user_id = str(current_user["_id"])
    result = cloudinary.uploader.upload(
        contents,
        public_id=user_id,
        folder=f"vibe/profile_photos/{user_id}",
        overwrite=True,
    )
    photo_url = result["secure_url"]

    users = get_users_collection()
    await users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"photo_url": photo_url, "updated_at": datetime.now(timezone.utc)}},
    )
    updated = await users.find_one({"_id": current_user["_id"]})
    return _user_to_dict(updated)


@router.get("/{user_id}")
async def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=404, detail="User not found")

    users = get_users_collection()
    user = await users.find_one({"_id": oid})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    requester_id = str(current_user["_id"])
    is_matched = False
    if requester_id != user_id:
        matches = get_matches_collection()
        match = await matches.find_one({"user_ids": {"$all": [requester_id, user_id]}})
        is_matched = match is not None

    spotify = user.get("spotify") or {}
    return {
        "user_id": str(user["_id"]),
        "display_name": user["display_name"],
        "age": user["age"],
        "city": user["city"],
        "bio": user.get("bio"),
        "gender": user.get("gender"),
        "top_genres": spotify.get("top_genres") or [],
        "top_artists": spotify.get("top_artists") or [],
        "photo_url": user.get("photo_url") if is_matched else None,
        "contact_info": user.get("contact_info") if is_matched else None,
    }
