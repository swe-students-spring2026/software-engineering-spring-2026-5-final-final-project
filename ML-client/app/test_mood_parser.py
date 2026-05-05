"""
Tests for mood_parser.py — covers parse_mood and rerank_tracks.

Usage (inside the ml-service container or with pipenv):
  pytest test_mood_parser.py -v
  docker exec -it ml-service pytest test_mood_parser.py -v
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from schemas import AudioProfile, WeatherData, Track
from mood_parser import parse_mood, rerank_tracks


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_weather():
    return WeatherData(temp=8.0, condition="light drizzle", humidity=81, city="New York")


@pytest.fixture
def sample_profile():
    return AudioProfile(
        valence=0.3,
        energy=0.4,
        danceability=0.35,
        tempo_min=70,
        tempo_max=100,
        genres=["sad-indie", "ambient"],
        reasoning="Cozy rainy day calls for low-energy introspective music.",
        search_queries=["rainy day indie sad piano", "lo-fi coffee shop study", "melancholic acoustic folk"],
    )


@pytest.fixture
def sample_tracks():
    return [
        Track(uri="spotify:track:aaa", name="Rainy Monday", artist="Artist A",
              album="Drizzle", preview_url=None, external_url="https://open.spotify.com/track/aaa"),
        Track(uri="spotify:track:bbb", name="Sunshine Pop", artist="Artist B",
              album="Happy", preview_url=None, external_url="https://open.spotify.com/track/bbb"),
        Track(uri="spotify:track:ccc", name="Soft Piano", artist="Artist C",
              album="Chill", preview_url=None, external_url="https://open.spotify.com/track/ccc"),
    ]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_gemini_response(payload: dict) -> MagicMock:
    """Return a mock Gemini response whose .text is a JSON string."""
    mock_response = MagicMock()
    mock_response.text = json.dumps(payload)
    return mock_response


def _make_gemini_response_text(text: str) -> MagicMock:
    mock_response = MagicMock()
    mock_response.text = text
    return mock_response


# ── parse_mood tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_parse_mood_returns_audio_profile(sample_weather):
    """parse_mood should return a valid AudioProfile when Gemini responds correctly."""
    fake_payload = {
        "valence": 0.3,
        "energy": 0.4,
        "danceability": 0.35,
        "tempo_min": 70,
        "tempo_max": 100,
        "genres": ["sad-indie", "ambient"],
        "reasoning": "Rainy + cozy mood calls for low-energy music.",
        "search_queries": ["rainy day lo-fi", "cozy indie sad"],
    }

    with patch("mood_parser.client") as mock_client:
        mock_client.models.generate_content.return_value = _make_gemini_response(fake_payload)
        profile = await parse_mood("cozy and a bit sad", sample_weather)

    assert isinstance(profile, AudioProfile)
    assert 0.0 <= profile.valence <= 1.0
    assert 0.0 <= profile.energy <= 1.0
    assert 0.0 <= profile.danceability <= 1.0
    assert profile.tempo_min < profile.tempo_max
    assert len(profile.genres) >= 1
    assert isinstance(profile.search_queries, list)
    assert len(profile.search_queries) >= 1


@pytest.mark.asyncio
async def test_parse_mood_strips_markdown_fences(sample_weather):
    """parse_mood should handle Gemini responses wrapped in markdown code fences."""
    fake_payload = {
        "valence": 0.8,
        "energy": 0.9,
        "danceability": 0.75,
        "tempo_min": 120,
        "tempo_max": 160,
        "genres": ["pop", "dance"],
        "reasoning": "High energy sunny day.",
        "search_queries": ["upbeat summer pop 2020s"],
    }

    wrapped = f"```json\n{json.dumps(fake_payload)}\n```"
    with patch("mood_parser.client") as mock_client:
        mock_client.models.generate_content.return_value = _make_gemini_response_text(wrapped)
        profile = await parse_mood("hyped and ready to go", sample_weather)

    assert profile.valence == 0.8
    assert profile.energy == 0.9
    assert "pop" in profile.genres


@pytest.mark.asyncio
async def test_parse_mood_raises_on_invalid_json(sample_weather):
    """parse_mood should raise an exception if Gemini returns invalid JSON."""
    with patch("mood_parser.client") as mock_client:
        mock_client.models.generate_content.return_value = _make_gemini_response_text(
            "Sorry, I cannot help with that."
        )
        with pytest.raises(Exception):
            await parse_mood("cozy", sample_weather)


@pytest.mark.asyncio
async def test_parse_mood_search_queries_populated(sample_weather):
    """parse_mood should produce non-empty search_queries when Gemini provides them."""
    fake_payload = {
        "valence": 0.5,
        "energy": 0.5,
        "danceability": 0.5,
        "tempo_min": 90,
        "tempo_max": 120,
        "genres": ["pop"],
        "reasoning": "Neutral mood.",
        "search_queries": ["neutral indie pop", "chill background music"],
    }

    with patch("mood_parser.client") as mock_client:
        mock_client.models.generate_content.return_value = _make_gemini_response(fake_payload)
        profile = await parse_mood("okay I guess", sample_weather)

    assert "neutral indie pop" in profile.search_queries
    assert "chill background music" in profile.search_queries


# ── rerank_tracks tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rerank_tracks_returns_all_tracks(sample_tracks):
    """rerank_tracks should return the same number of tracks regardless of AI order."""
    ranked_response = [
        {"uri": "spotify:track:ccc", "reason": "Soft piano suits the cozy vibe"},
        {"uri": "spotify:track:aaa", "reason": "Rainy theme fits perfectly"},
        {"uri": "spotify:track:bbb", "reason": "Upbeat but still mellow"},
    ]

    with patch("mood_parser.client") as mock_client:
        mock_client.models.generate_content.return_value = _make_gemini_response_text(
            json.dumps(ranked_response)
        )
        result = await rerank_tracks("cozy and a bit sad", sample_tracks)

    assert len(result) == len(sample_tracks)
    uris = [t.uri for t in result]
    assert "spotify:track:aaa" in uris
    assert "spotify:track:bbb" in uris
    assert "spotify:track:ccc" in uris


@pytest.mark.asyncio
async def test_rerank_tracks_populates_reason(sample_tracks):
    """rerank_tracks should set the `reason` field on each Track."""
    ranked_response = [
        {"uri": "spotify:track:aaa", "reason": "Great rainy day track"},
        {"uri": "spotify:track:ccc", "reason": "Soft piano is soothing"},
        {"uri": "spotify:track:bbb", "reason": "Cheerful, slight mood mismatch"},
    ]

    with patch("mood_parser.client") as mock_client:
        mock_client.models.generate_content.return_value = _make_gemini_response_text(
            json.dumps(ranked_response)
        )
        result = await rerank_tracks("cozy and a bit sad", sample_tracks)

    reasons = [t.reason for t in result]
    assert all(r is not None for r in reasons)
    assert "Great rainy day track" in reasons


@pytest.mark.asyncio
async def test_rerank_tracks_fallback_on_error(sample_tracks):
    """rerank_tracks should return the original order if Gemini fails."""
    with patch("mood_parser.client") as mock_client:
        mock_client.models.generate_content.side_effect = RuntimeError("API down")
        result = await rerank_tracks("cozy and a bit sad", sample_tracks)

    assert len(result) == len(sample_tracks)
    assert result[0].uri == sample_tracks[0].uri


@pytest.mark.asyncio
async def test_rerank_tracks_empty_input():
    """rerank_tracks should return an empty list if given no tracks."""
    result = await rerank_tracks("any mood", [])
    assert result == []


@pytest.mark.asyncio
async def test_rerank_tracks_missing_uri_in_response(sample_tracks):
    """rerank_tracks should safely skip unknown URIs returned by Gemini."""
    ranked_response = [
        {"uri": "spotify:track:aaa", "reason": "Good fit"},
        {"uri": "spotify:track:UNKNOWN", "reason": "This URI does not exist"},
    ]

    with patch("mood_parser.client") as mock_client:
        mock_client.models.generate_content.return_value = _make_gemini_response_text(
            json.dumps(ranked_response)
        )
        result = await rerank_tracks("cozy", sample_tracks)

    uris = [t.uri for t in result]
    assert "spotify:track:UNKNOWN" not in uris
    # All original tracks should still be present (safety net appends missed ones)
    assert len(result) == len(sample_tracks)