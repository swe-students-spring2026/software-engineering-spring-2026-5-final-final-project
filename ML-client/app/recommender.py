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

SAFE_LIMIT = 10  # Spotify search max per call


async def get_tracks(profile: AudioProfile, limit: int = 20) -> list[Track]:
    """
    Search Spotify using AI-generated queries (from AudioProfile.search_queries)
    with genre-based queries as fallback. Returns deduplicated tracks up to `limit`.
    """
    # ── Build query list ──────────────────────────────────────────────────────
    # Priority 1: AI-generated natural-language queries
    queries: list[str] = list(profile.search_queries)

    # Priority 2: Genre-based fallbacks
    if profile.genres:
        queries.append(" ".join(g.replace("-", " ") for g in profile.genres[:2]))
        queries.append(profile.genres[0].replace("-", " "))

    # Priority 3: Universal fallback
    queries.append("chill music")

    # ── Search Spotify ────────────────────────────────────────────────────────
    raw_tracks: list[dict] = []
    seen_uris: set[str] = set()

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

    # ── Convert to Track schema ───────────────────────────────────────────────
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
                reason=None,  # filled in by rerank_tracks later
            )
        )

    return tracks