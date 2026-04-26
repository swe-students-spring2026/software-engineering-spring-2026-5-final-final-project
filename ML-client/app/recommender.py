import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from schemas import AudioProfile, Track
from config import settings

# Client credentials flow — no user login needed for recommendations
_sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
    )
)


def _safe_genres(genres: list[str]) -> list[str]:
    """
    Spotify only accepts genres from its approved seed list.
    Filter to known-good ones; fall back to ['pop'] if nothing matches.
    """
    available = set(_sp.recommendation_genre_seeds().get("genres", []))
    filtered = [g for g in genres if g in available]
    return filtered[:2] if filtered else ["pop"]


async def get_tracks(profile: AudioProfile, limit: int = 20) -> list[Track]:
    """Query Spotify recommendations endpoint using the audio profile."""

    seed_genres = _safe_genres(profile.genres)

    results = _sp.recommendations(
        seed_genres=seed_genres,
        target_valence=profile.valence,
        target_energy=profile.energy,
        target_danceability=profile.danceability,
        target_tempo=(profile.tempo_min + profile.tempo_max) / 2,
        min_tempo=profile.tempo_min,
        max_tempo=profile.tempo_max,
        limit=limit,
    )

    tracks: list[Track] = []
    for t in results.get("tracks", []):
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

    # Optionally enrich with audio features for display
    if tracks:
        uris = [t.uri for t in tracks]
        features = _sp.audio_features(uris) or []
        for track, feat in zip(tracks, features):
            if feat:
                track.valence = feat.get("valence")
                track.energy = feat.get("energy")

    return tracks
