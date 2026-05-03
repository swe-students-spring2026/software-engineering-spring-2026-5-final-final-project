import logging
from datetime import datetime, timezone

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from app.config import get_settings
from app.database import get_users_collection

logger = logging.getLogger(__name__)
settings = get_settings()


def _build_spotify_client(access_token: str) -> spotipy.Spotify:
    """Return an authenticated Spotify client for a given access token."""
    return spotipy.Spotify(auth=access_token)


def _extract_top_artists(raw_artists: list[dict]) -> list[dict]:
    """
    Distil the raw spotipy artist objects down to {id, name}.

    Args:
        raw_artists: Items list from spotipy current_user_top_artists().

    Returns:
        List of dicts with keys 'id' and 'name'.
    """
    return [{"id": a["id"], "name": a["name"]} for a in raw_artists]


def _extract_top_genres(raw_artists: list[dict]) -> list[str]:
    """
    Flatten and deduplicate genre tags from all top artists.

    Args:
        raw_artists: Items list from spotipy current_user_top_artists().

    Returns:
        Deduplicated list of genre strings, preserving first-seen order.
    """
    seen: set[str] = set()
    genres: list[str] = []
    for artist in raw_artists:
        for genre in artist.get("genres", []):
            if genre not in seen:
                seen.add(genre)
                genres.append(genre)
    return genres


def _average_audio_features(feature_list: list[dict | None]) -> dict | None:
    """
    Average energy, valence, danceability, and tempo across a list of tracks.
    Skips None entries (tracks for which Spotify returned no data).

    Args:
        feature_list: Raw list returned by spotipy audio_features().

    Returns:
        Dict with keys energy, valence, danceability, tempo (all floats),
        or None if no valid entries exist.
    """
    valid = [f for f in feature_list if f is not None]
    if not valid:
        return None

    keys = ("energy", "valence", "danceability", "tempo")
    return {k: sum(f[k] for f in valid) / len(valid) for k in keys}


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


async def pull_user_data(user_id: str, access_token: str) -> None:
    """
    Fetch and persist a user's Spotify music data using their stored access token.

    Pulls:
      - Top 50 artists (long_term)  → spotify.top_artists, spotify.top_genres
      - Audio features averaged over top 50 tracks (medium_term)
                                    → spotify.audio_features
      - Updates spotify.last_synced

    Args:
        user_id: The MongoDB user _id string.

    Raises:
        RuntimeError: If the user has no access token or Spotify calls fail.
    """
    users = get_users_collection()
    sp = _build_spotify_client(access_token)

    try:
        # ── Top artists ──────────────────────────────────────────────────────
        artists_response = sp.current_user_top_artists(
            limit=50, time_range="long_term"
        )
        raw_artists: list[dict] = artists_response.get("items", [])

        top_artists = _extract_top_artists(raw_artists)
        top_genres = _extract_top_genres(raw_artists)

        # ── Audio features ───────────────────────────────────────────────────
        tracks_response = sp.current_user_top_tracks(
            limit=50, time_range="medium_term"
        )
        track_ids = [t["id"] for t in tracks_response.get("items", [])]

        audio_features: dict | None = None
        if track_ids:
            raw_features = sp.audio_features(track_ids)   # list[dict | None]
            audio_features = _average_audio_features(raw_features)

    except Exception as exc:
        logger.error("Spotify data pull failed for user %s: %s", user_id, exc)
        raise RuntimeError("Failed to pull Spotify data") from exc

    # ── Persist ──────────────────────────────────────────────────────────────
    await users.update_one(
        {"_id": user_id},
        {
            "$set": {
                "spotify.top_artists": top_artists,
                "spotify.top_genres": top_genres,
                "spotify.audio_features": audio_features,
                "spotify.last_synced": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )

    logger.info(
        "Pulled Spotify data for user %s: %d artists, %d genres",
        user_id,
        len(top_artists),
        len(top_genres),
    )