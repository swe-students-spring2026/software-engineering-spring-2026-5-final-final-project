import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from schemas import AudioProfile, Track
from config import settings

_sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
    )
)

SAFE_LIMIT = 10


def _search_seed_tracks(queries: list[str], n: int = 3) -> list[str]:
    """Resolve search queries → Spotify track IDs for use as recommendation seeds."""
    seed_ids: list[str] = []
    for query in queries[:n]:
        try:
            results = _sp.search(q=query, type="track", limit=1)
            items = results.get("tracks", {}).get("items", [])
            if items:
                seed_ids.append(items[0]["id"])
        except Exception:
            continue
    return seed_ids


def _raw_to_track(t: dict) -> Track:
    return Track(
        uri=t["uri"],
        name=t["name"],
        artist=t["artists"][0]["name"],
        album=t["album"]["name"],
        preview_url=t.get("preview_url"),
        external_url=t["external_urls"]["spotify"],
        reason=None,  # filled by rerank_tracks later
    )


async def get_tracks(profile: AudioProfile, limit: int = 20) -> list[Track]:
    """
    Recommend tracks from Spotify using AudioProfile audio features + seeds.
    Seeds are resolved from AI search_queries (track IDs) + genres.
    Falls back to pure search if recommendations fail.
    """
    seen_uris: set[str] = set()
    raw_tracks: list[dict] = []

    # ── Build seeds (max 5 total across tracks + genres) ─────────────────────
    seed_tracks = _search_seed_tracks(profile.search_queries, n=3)  # up to 3
    seed_genres = list(profile.genres or [])[:2]                    # up to 2

    # ── Attempt recommendations ───────────────────────────────────────────────
    if seed_tracks or seed_genres:
        try:
            results = _sp.recommendations(
                seed_tracks=seed_tracks or None,
                seed_genres=seed_genres or None,
                limit=min(limit, 20),  # Spotify max is 100
                target_valence=profile.valence,
                target_energy=profile.energy,
                target_danceability=profile.danceability,
                min_tempo=profile.tempo_min,
                max_tempo=profile.tempo_max,
            )
            for t in results.get("tracks", []):
                if t["uri"] not in seen_uris:
                    seen_uris.add(t["uri"])
                    raw_tracks.append(t)
        except Exception:
            pass  # fall through to search fallback below

    # ── Search fallback (if recommendations failed or returned too few) ───────
    if len(raw_tracks) < limit:
        needed = limit - len(raw_tracks)

        # Build fallback query list (same priority as before)
        fallback_queries: list[str] = list(profile.search_queries)
        if profile.genres:
            fallback_queries.append(" ".join(g.replace("-", " ") for g in profile.genres[:2]))
            fallback_queries.append(profile.genres[0].replace("-", " "))
        fallback_queries.append("chill music")

        for query in fallback_queries:
            if len(raw_tracks) >= limit:
                break
            try:
                results = _sp.search(q=query, type="track", limit=SAFE_LIMIT)
                items = results.get("tracks", {}).get("items", [])
                for t in items:
                    if t["uri"] not in seen_uris and needed > 0:
                        seen_uris.add(t["uri"])
                        raw_tracks.append(t)
                        needed -= 1
            except Exception:
                continue

    if not raw_tracks:
        return []

    return [_raw_to_track(t) for t in raw_tracks[:limit]]