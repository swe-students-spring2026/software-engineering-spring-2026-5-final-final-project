import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from schemas import AudioProfile, Track
from config import settings

# Client credentials flow — no user login needed for search
_sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
    )
)

async def get_tracks(profile: AudioProfile, limit: int = 20) -> list[Track]:
    """
    Search Spotify by genre keywords and return matched tracks.
    """
    SAFE_LIMIT = 10

    raw_tracks = []

    # Run up to 3 searches with different queries to get enough tracks
    queries = []
    if profile.genres:
        queries.append(" ".join(g.replace("-", " ") for g in profile.genres[:2]))
        queries.append(profile.genres[0].replace("-", " "))
    queries.append("chill music")

    seen_uris = set()
    for query in queries:
        if len(raw_tracks) >= limit:
            break
        try:
            results = _sp.search(q=query, type="track", limit=SAFE_LIMIT)
            items = results.get("tracks", {}).get("items", [])
            for t in items:
                if t["uri"] not in seen_uris:
                    seen_uris.add(t["uri"])
                    raw_tracks.append(t)
        except Exception:
            continue

    if not raw_tracks:
        return []

    tracks: list[Track] = []
    for t in raw_tracks[:limit]:
        tracks.append(
            Track(
                uri=t["uri"],
                name=t["name"],
                artist=t["artists"][0]["name"],
                album=t["album"]["name"],
                preview_url=t.get("preview_url"),
                external_url=t["external_urls"]["spotify"],
            )
        )

    return tracks