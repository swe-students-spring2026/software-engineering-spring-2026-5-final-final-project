import json
import httpx
from schemas import AudioProfile, WeatherData
from config import settings


# GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
PROMPT_TEMPLATE = """You are a music mood analyst. Given a user's mood and weather, 
return Spotify audio feature targets as JSON only — no explanation, no markdown.

User mood: "{mood}"
Weather: {temp}°C, {condition}, humidity {humidity}%

Rules:
- Mood is PRIMARY. Weather is a secondary nudge only.
- Cold/rainy nudges valence slightly lower. Sunny/warm nudges energy slightly higher.
- Pick 2 Spotify genre strings (e.g. "sad-indie", "ambient", "pop", "chill", "folk").

Return ONLY this JSON:
{{
  "valence": 0.0-1.0,
  "energy": 0.0-1.0,
  "danceability": 0.0-1.0,
  "tempo_min": <int>,
  "tempo_max": <int>,
  "genres": ["genre1", "genre2"],
  "reasoning": "one sentence"
}}"""


# async def parse_mood(mood: str, weather: WeatherData) -> AudioProfile:
#     prompt = PROMPT_TEMPLATE.format(
#         mood=mood,
#         temp=weather.temp,
#         condition=weather.condition,
#         humidity=weather.humidity,
#     )

#     payload = {
#         "contents": [{"parts": [{"text": prompt}]}],
#         "generationConfig": {"temperature": 0.4}
#     }

#     async with httpx.AsyncClient() as client:
#         resp = await client.post(
#             f"{GEMINI_URL}?key={settings.gemini_api_key}",
#             json=payload,
#             timeout=15,
#         )
#         resp.raise_for_status()

#     raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

#     # Strip markdown fences if present
#     if raw.startswith("```"):
#         raw = raw.split("```")[1]
#         if raw.startswith("json"):
#             raw = raw[4:]

#     return AudioProfile(**json.loads(raw))
from google import genai
import os
import json
from schemas import AudioProfile, WeatherData
from config import settings

client = genai.Client(api_key=settings.gemini_api_key)

async def parse_mood(mood: str, weather: WeatherData) -> AudioProfile:
    prompt = PROMPT_TEMPLATE.format(
        mood=mood,
        temp=weather.temp,
        condition=weather.condition,
        humidity=weather.humidity,
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "temperature": 0.4,
        }
    )

    raw = response.text.strip()

    # Clean JSON (important)
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return AudioProfile(**json.loads(raw))