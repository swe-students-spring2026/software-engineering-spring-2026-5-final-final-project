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
    """
    Redirect the authenticated user to the Spotify OAuth authorization page.

    Encodes user_id into a short-lived signed JWT passed as the OAuth `state`
    parameter; verified in /callback to identify the returning user without
    requiring a server-side session.
    """
    user_id = str(current_user["_id"])

    # Short-lived state token (10 min) — encode user identity for the callback
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
    """
    Handle the Spotify OAuth callback.

    Verifies the `state` JWT to recover the user_id (no login cookie needed
    here — the request originates from Spotify's redirect, not the browser's
    normal session).  Exchanges the authorization code for tokens and stores
    them, then redirects the user to the profile-setup page.
    """
    # If Spotify returned an error (e.g. user denied access)
    if error:
        logger.warning("Spotify OAuth error: %s", error)
        raise HTTPException(status_code=400, detail=f"Spotify authorization failed: {error}")

    # Verify and decode the state JWT
    try:
        payload = decode_jwt(state)
        user_id = payload["user_id"]
    except Exception as exc:
        logger.error("Invalid or expired state token: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")

    # Exchange auth code for tokens and persist to DB
    try:
        await spotify_service.exchange_code_for_tokens(user_id=user_id, code=code)
    except RuntimeError as exc:
        logger.error("Token exchange failed for user %s: %s", user_id, exc)
        raise HTTPException(status_code=502, detail="Failed to connect Spotify account")

    logger.info("Spotify connected for user %s, redirecting to profile setup", user_id)
    return RedirectResponse(url=f"{settings.frontend_url}/profile/setup")


@router.post("/disconnect")
async def spotify_disconnect(current_user: dict = Depends(get_current_user)):
    """
    Disconnect the current user's Spotify account.

    Clears stored tokens and audio data; sets is_spotify_connected=false so
    the user is hidden from the discovery feed until they reconnect.
    """
    user_id = str(current_user["_id"])

    await spotify_service.disconnect_spotify(user_id=user_id)

    logger.info("User %s disconnected Spotify", user_id)
    return {"detail": "Spotify account disconnected"}