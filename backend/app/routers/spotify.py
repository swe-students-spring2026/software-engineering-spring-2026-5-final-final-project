import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.auth import encode_jwt, decode_jwt, get_current_user
from app.config import get_settings
from app.services import spotify as spotify_service

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/spotify", tags=["spotify"])


@router.get("/connect")
async def spotify_connect(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    state_token = encode_jwt({"user_id": user_id}, expiry_minutes=10)
    auth_url = spotify_service.get_authorization_url(state=state_token)
    logger.info("Redirecting user %s to Spotify OAuth", user_id)
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def spotify_callback(
    code: str = Query(..., description="Authorization code from Spotify"),
    state: str = Query(..., description="Signed state JWT from /connect"),
    error: str | None = Query(None, description="Error returned by Spotify"),
):
    if error:
        logger.warning("Spotify OAuth error: %s", error)
        raise HTTPException(status_code=400, detail=f"Spotify authorization failed: {error}")

    try:
        payload = decode_jwt(state)
        user_id = payload["user_id"]
    except Exception as exc:
        logger.error("Invalid or expired state token: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")

    try:
        token_info = await spotify_service.exchange_code_for_tokens(user_id=user_id, code=code)
    except RuntimeError as exc:
        logger.error("Token exchange failed for user %s: %s", user_id, exc)
        raise HTTPException(status_code=502, detail="Failed to connect Spotify account")

    # Pull initial music data (top artists, genres, audio features).
    # Non-fatal: tokens are already saved so the user can still proceed.
    # The weekly scheduler will retry on the next cycle if this fails.
    try:
        await spotify_service.pull_user_data(
            user_id=user_id,
            access_token=token_info["access_token"],
        )
    except RuntimeError as exc:
        logger.warning("Initial Spotify data pull failed for user %s: %s", user_id, exc)

    logger.info("Spotify connected for user %s, redirecting to profile setup", user_id)
    return RedirectResponse(url=f"{settings.frontend_url}/profile/setup")


@router.post("/disconnect")
async def spotify_disconnect(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    await spotify_service.disconnect_spotify(user_id=user_id)
    logger.info("User %s disconnected Spotify", user_id)
    return {"detail": "Spotify account disconnected"}