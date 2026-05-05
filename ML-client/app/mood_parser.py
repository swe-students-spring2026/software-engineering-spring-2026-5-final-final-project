import json
import os
from google import genai
from schemas import AudioProfile, WeatherData, Track
from config import settings


# ── Gemini client ─────────────────────────────────────────────────────────────

client = genai.Client(api_key=settings.gemini_api_key)


# ── Prompt templates ──────────────────────────────────────────────────────────

PROMPT_TEMPLATE = """You are a music mood analyst. Given a user's mood and weather,
return Spotify audio feature targets as JSON only — no explanation, no markdown.

User mood: "{mood}"
Weather: {temp}°C, {condition}, humidity {humidity}%

Rules:
- Mood is PRIMARY. Weather is a secondary nudge only.
- Cold/rainy nudges valence slightly lower. Sunny/warm nudges energy slightly higher.
- Pick 2 Spotify genre strings (e.g. "sad-indie", "ambient", "pop", "chill", "folk").
- Generate 3–5 specific Spotify search queries that would surface great tracks for this mood.
  Queries should be concrete (e.g. "rainy day lo-fi coffee shop", "upbeat indie summer 2020s").
  Do NOT just use genre names alone.

Return ONLY this JSON:
{{
  "valence": 0.0-1.0,
  "energy": 0.0-1.0,
  "danceability": 0.0-1.0,
  "tempo_min": <int>,
  "tempo_max": <int>,
  "genres": ["genre1", "genre2"],
  "reasoning": "one sentence",
  "search_queries": ["query1", "query2", "query3"]
}}"""

RERANK_PROMPT_TEMPLATE = """You are a music curator. A user is feeling "{mood}".
Below is a list of tracks fetched from Spotify. Select the best-fitting tracks
for this mood and return them re-ranked from most to least fitting.

Tracks (JSON array):
{tracks_json}

Rules:
- Keep ALL tracks in your output (do not drop any).
- For each track add a short "reason" (≤ 12 words) explaining why it fits the mood.
- Return ONLY a JSON array — no markdown, no explanation.

Return format:
[
  {{"uri": "<track_uri>", "reason": "<short reason>"}},
  ...
]"""


# ── parse_mood ────────────────────────────────────────────────────────────────

async def parse_mood(mood: str, weather: WeatherData) -> AudioProfile:
    """Call Gemini to convert mood + weather into an AudioProfile with search queries."""
    prompt = PROMPT_TEMPLATE.format(
        mood=mood,
        temp=weather.temp,
        condition=weather.condition,
        humidity=weather.humidity,
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={"temperature": 0.4},
    )

    raw = response.text.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return AudioProfile(**json.loads(raw))


# ── rerank_tracks ─────────────────────────────────────────────────────────────

async def rerank_tracks(mood: str, tracks: list[Track]) -> list[Track]:
    """
    Send a list of tracks to Gemini and get them back re-ranked by mood fit.
    Each track in the returned list will have its `reason` field populated.
    Falls back to the original order if Gemini fails.
    """
    if not tracks:
        return tracks

    # Build a minimal representation to avoid huge token usage
    tracks_input = [
        {"uri": t.uri, "name": t.name, "artist": t.artist, "album": t.album}
        for t in tracks
    ]

    prompt = RERANK_PROMPT_TEMPLATE.format(
        mood=mood,
        tracks_json=json.dumps(tracks_input, ensure_ascii=False, indent=2),
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"temperature": 0.3},
        )

        raw = response.text.strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        ranked_data: list[dict] = json.loads(raw)

        # Build a lookup: uri → original Track object
        track_map = {t.uri: t for t in tracks}

        reranked: list[Track] = []
        for item in ranked_data:
            uri = item.get("uri")
            reason = item.get("reason")
            if uri and uri in track_map:
                track = track_map[uri].model_copy(update={"reason": reason})
                reranked.append(track)

        # Append any tracks Gemini forgot to include (safety net)
        ranked_uris = {t.uri for t in reranked}
        for t in tracks:
            if t.uri not in ranked_uris:
                reranked.append(t)

        return reranked

    except Exception:
        # Non-fatal fallback — return original order unchanged
        return tracks