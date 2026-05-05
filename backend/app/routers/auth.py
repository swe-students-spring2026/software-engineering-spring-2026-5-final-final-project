from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.auth import encode_jwt, get_current_user, hash_password, verify_password
from app.database import get_users_collection
from app.models.schemas import LoginRequest, RegisterRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])

_COOKIE = "vibe_token"


def _set_auth_cookie(response: JSONResponse, token: str) -> None:
    response.set_cookie(
        key=_COOKIE,
        value=token,
        httponly=True,
        samesite="Lax",
        secure=False,
        max_age=7 * 24 * 3600,
    )


def _user_to_dict(user: dict) -> dict:
    spotify = user.get("spotify") or {}
    return {
        "user_id": str(user["_id"]),
        "email": user["email"],
        "display_name": user["display_name"],
        "age": user["age"],
        "city": user["city"],
        "bio": user.get("bio"),
        "gender": user.get("gender"),
        "gender_preference": user.get("gender_preference"),
        "age_range_preference": user.get("age_range_preference"),
        "photo_url": user.get("photo_url"),
        "contact_info": user.get("contact_info") or {"phone": None, "instagram": None},
        "top_genres": spotify.get("top_genres") or [],
        "top_artists": spotify.get("top_artists") or [],
        "audio_features": spotify.get("audio_features"),
        "is_spotify_connected": user.get("is_spotify_connected", False),
        "spotify_last_synced": spotify.get("last_synced"),
        "likes_sent_today": user.get("likes_sent_today", 0),
        "created_at": user.get("created_at", datetime.now(timezone.utc)),
    }


@router.post("/register", status_code=201)
async def register(body: RegisterRequest):
    users = get_users_collection()
    if await users.find_one({"email": body.email}):
        raise HTTPException(status_code=409, detail="Email already registered")

    now = datetime.now(timezone.utc)
    doc = {
        "email": body.email,
        "password_hash": hash_password(body.password),
        "display_name": body.display_name,
        "age": body.age,
        "city": body.city,
        "bio": None,
        "gender": None,
        "gender_preference": None,
        "age_range_preference": None,
        "photo_url": None,
        "contact_info": {"phone": None, "instagram": None},
        "spotify": {
            "access_token": None,
            "refresh_token": None,
            "top_artists": [],
            "top_genres": [],
            "audio_features": None,
            "last_synced": None,
        },
        "is_spotify_connected": False,
        "likes_sent_today": 0,
        "likes_reset_at": now,
        "created_at": now,
        "updated_at": now,
    }
    result = await users.insert_one(doc)
    user_id = str(result.inserted_id)
    token = encode_jwt({"user_id": user_id})

    response = JSONResponse(content={"user_id": user_id}, status_code=201)
    _set_auth_cookie(response, token)
    return response


@router.post("/login")
async def login(body: LoginRequest):
    users = get_users_collection()
    user = await users.find_one({"email": body.email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = str(user["_id"])
    token = encode_jwt({"user_id": user_id})

    response = JSONResponse(content={"user_id": user_id})
    _set_auth_cookie(response, token)
    return response


@router.post("/logout")
async def logout():
    response = JSONResponse(content={"detail": "Logged out"})
    response.delete_cookie(_COOKIE)
    return response


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return _user_to_dict(current_user)
