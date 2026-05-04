from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException

from app.config import get_settings


def encode_jwt(payload: dict, expiry_minutes: int | None = None) -> str:
    data = payload.copy()
    if expiry_minutes is not None:
        data["exp"] = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
    return jwt.encode(data, get_settings().jwt_secret, algorithm="HS256")


def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc


async def get_current_user() -> dict:
    # Stub — overridden via dependency_overrides in tests.
    # Full implementation (cookie parsing, DB lookup) belongs to Jack / auth.py owner.
    raise HTTPException(status_code=401, detail="Not authenticated")
