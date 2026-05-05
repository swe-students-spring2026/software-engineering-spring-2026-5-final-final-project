from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from bson import ObjectId
from fastapi import HTTPException, Request
from passlib.context import CryptContext

from app.config import get_settings
from app.database import get_users_collection

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def encode_jwt(payload: dict[str, Any], expiry_minutes: int | None = None) -> str:
    settings = get_settings()
    data = payload.copy()
    if expiry_minutes is not None:
        exp = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
    else:
        exp = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expiry_days)
    data["exp"] = exp
    return jwt.encode(data, settings.jwt_secret, algorithm="HS256")


def decode_jwt(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("vibe_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_jwt(token)
        user_id = payload.get("user_id")
        if not user_id:
            raise ValueError("Missing user_id in token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    users = get_users_collection()
    user = await users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
