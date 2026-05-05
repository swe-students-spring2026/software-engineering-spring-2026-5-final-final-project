"""
Tests for recommender.py — covers get_tracks.
"""
import pytest
from unittest.mock import MagicMock, patch
from schemas import AudioProfile


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_profile():
    return AudioProfile(
        valence=0.7,
        energy=0.8,
        danceability=0.6,
        tempo_min=100,
        tempo_max=140,
        genres=["pop", "dance"],
        reasoning="Upbeat mood calls for energetic music.",
        search_queries=["upbeat summer pop 2020s", "feel good indie dance"],
    )


@pytest.fixture
def sample_profile_no_queries():
    return AudioProfile(
        valence=0.5,
        energy=0.5,
        danceability=0.5,
        tempo_min=80,
        tempo_max=120,
        genres=["ambient"],
        reasoning="Neutral mood.",
        search_queries=[],
    )


def _make_spotify_track(uri="spotify:track:abc", name="Track A", artist="Artist A"):
    return {
        "uri": uri,
        "name": name,
        "artists": [{"name": artist}],
        "album": {"name": "Album A"},
        "preview_url": None,
        "external_urls": {"spotify": f"https://open.spotify.com/track/{uri.split(':')[-1]}"},
    }


# ── get_tracks ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_tracks_returns_tracks(sample_profile):
    """get_tracks should return a list of Track objects on success."""
    fake_items = [_make_spotify_track(f"spotify:track:{i}", f"Track {i}") for i in range(5)]
    fake_results = {"tracks": {"items": fake_items}}

    with patch("recommender._sp") as mock_sp:
        mock_sp.search.return_value = fake_results
        from recommender import get_tracks
        tracks = await get_tracks(sample_profile, limit=5)

    assert len(tracks) > 0
    assert tracks[0].name == "Track 0"
    assert tracks[0].artist == "Artist A"


@pytest.mark.asyncio
async def test_get_tracks_deduplicates(sample_profile):
    """get_tracks should not return duplicate tracks."""
    # Same URI from two different queries
    dup_track = _make_spotify_track("spotify:track:DUP", "Dup Track")
    fake_results = {"tracks": {"items": [dup_track]}}

    with patch("recommender._sp") as mock_sp:
        mock_sp.search.return_value = fake_results
        from recommender import get_tracks
        tracks = await get_tracks(sample_profile, limit=10)

    uris = [t.uri for t in tracks]
    assert len(uris) == len(set(uris))


@pytest.mark.asyncio
async def test_get_tracks_returns_empty_on_no_results(sample_profile):
    """get_tracks should return an empty list when Spotify returns nothing."""
    with patch("recommender._sp") as mock_sp:
        mock_sp.search.return_value = {"tracks": {"items": []}}
        from recommender import get_tracks
        tracks = await get_tracks(sample_profile, limit=5)

    assert tracks == []


@pytest.mark.asyncio
async def test_get_tracks_handles_spotify_exception(sample_profile):
    """get_tracks should not crash if Spotify raises an exception; falls back to chill fallback."""
    # All queries fail except potentially the 'chill music' fallback
    with patch("recommender._sp") as mock_sp:
        mock_sp.search.side_effect = Exception("Spotify API error")
        from recommender import get_tracks
        tracks = await get_tracks(sample_profile, limit=5)

    # Should return empty list gracefully
    assert tracks == []


@pytest.mark.asyncio
async def test_get_tracks_uses_genre_fallback(sample_profile_no_queries):
    """get_tracks should fall back to genre-based queries when search_queries is empty."""
    fake_items = [_make_spotify_track("spotify:track:g1", "Genre Track")]
    fake_results = {"tracks": {"items": fake_items}}

    with patch("recommender._sp") as mock_sp:
        mock_sp.search.return_value = fake_results
        from recommender import get_tracks
        tracks = await get_tracks(sample_profile_no_queries, limit=5)

    assert len(tracks) > 0


@pytest.mark.asyncio
async def test_get_tracks_respects_limit(sample_profile):
    """get_tracks should not return more tracks than the specified limit."""
    fake_items = [_make_spotify_track(f"spotify:track:{i}", f"Track {i}") for i in range(10)]
    fake_results = {"tracks": {"items": fake_items}}

    with patch("recommender._sp") as mock_sp:
        mock_sp.search.return_value = fake_results
        from recommender import get_tracks
        tracks = await get_tracks(sample_profile, limit=3)

    assert len(tracks) <= 3
