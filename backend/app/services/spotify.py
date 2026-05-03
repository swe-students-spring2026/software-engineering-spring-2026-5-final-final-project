import logging
from datetime import datetime, timezone

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from app.config import get_settings
from app.database import get_users_collection

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_oauth_manager(state: str | None = None) -> SpotifyOAuth:
    """Return a SpotifyOAuth instance. Optionally embed a state token."""
    return SpotifyOAuth(
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
        redirect_uri=settings.spotify_redirect_uri,
        scope=(
            "user-top-read "
            "user-read-private "
            "user-read-email"
        ),
        state=state,
        cache_handler=spotipy.cache_handler.MemoryCacheHandler(),
        show_dialog=True,
    )


def get_authorization_url(state: str) -> str:
    """
    Build and return the Spotify OAuth authorization URL.

    Args:
        state: A signed JWT string encoding the user_id, to be verified on callback.

    Returns:
        The full Spotify authorization URL to redirect the user to.
    """
    oauth = _get_oauth_manager(state=state)
    auth_url = oauth.get_authorize_url()
    logger.info("Generated Spotify authorization URL")
    return auth_url


async def exchange_code_for_tokens(user_id: str, code: str) -> dict:
    """
    Exchange the OAuth authorization code for access/refresh tokens and
    persist them to the user document.

    Args:
        user_id: The MongoDB user _id string.
        code:    The authorization code returned by Spotify in the callback.

    Returns:
        The token info dict returned by spotipy
        (keys: access_token, refresh_token, expires_at, …).

    Raises:
        RuntimeError: If the token exchange fails.
    """
    oauth = _get_oauth_manager()

    try:
        token_info = oauth.get_access_token(code, as_dict=True, check_cache=False)
    except Exception as exc:
        logger.error("Spotify token exchange failed: %s", exc)
        raise RuntimeError("Failed to exchange Spotify authorization code") from exc

    users = get_users_collection()
    await users.update_one(
        {"_id": user_id},
        {
            "$set": {
                "spotify.access_token": token_info["access_token"],
                "spotify.refresh_token": token_info.get("refresh_token"),
                "is_spotify_connected": True,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )

    logger.info("Stored Spotify tokens for user %s", user_id)
    return token_info


async def disconnect_spotify(user_id: str) -> None:
    """
    Clear Spotify tokens and mark the user as disconnected.

    Args:
        user_id: The MongoDB user _id string.
    """
    users = get_users_collection()
    await users.update_one(
        {"_id": user_id},
        {
            "$set": {
                "spotify.access_token": None,
                "spotify.refresh_token": None,
                "spotify.top_artists": [],
                "spotify.top_genres": [],
                "spotify.audio_features": None,
                "spotify.last_synced": None,
                "is_spotify_connected": False,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    logger.info("Disconnected Spotify for user %s", user_id)