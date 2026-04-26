"""
Run this inside the ml-service container to test mood_parser in isolation.

Usage:
  docker exec -it ml-service python test_mood_parser.py
"""

import asyncio
from schemas import WeatherData
from mood_parser import parse_mood

# ── Test cases ────────────────────────────────────────────────────────────────

TEST_CASES = [
    {
        "label": "Cozy + rainy",
        "mood": "cozy and a bit sad",
        "weather": WeatherData(temp=8.0, condition="light drizzle", humidity=81, city="New York"),
    },
    {
        "label": "Energetic + sunny",
        "mood": "hyped and ready to go",
        "weather": WeatherData(temp=28.0, condition="clear sky", humidity=30, city="LA"),
    },
    {
        "label": "Conflict: calm mood + stormy weather",
        "mood": "peaceful and relaxed",
        "weather": WeatherData(temp=12.0, condition="thunderstorm", humidity=90, city="London"),
    },
    {
        "label": "Romantic + mild evening",
        "mood": "romantic and warm",
        "weather": WeatherData(temp=18.0, condition="few clouds", humidity=55, city="Paris"),
    },
]


async def run_tests():
    print("=" * 60)
    print("  mood_parser.py — isolation tests")
    print("=" * 60)

    passed = 0
    failed = 0

    for i, case in enumerate(TEST_CASES, 1):
        print(f"\nTest {i}: {case['label']}")
        print(f"  Mood    : {case['mood']}")
        print(f"  Weather : {case['weather'].temp}°C, {case['weather'].condition}")

        try:
            profile = await parse_mood(case["mood"], case["weather"])

            print(f"  ✅ Claude responded successfully")
            print(f"     valence      : {profile.valence}")
            print(f"     energy       : {profile.energy}")
            print(f"     danceability : {profile.danceability}")
            print(f"     tempo        : {profile.tempo_min}–{profile.tempo_max} bpm")
            print(f"     genres       : {profile.genres}")
            print(f"     reasoning    : {profile.reasoning}")

            # Basic sanity checks
            assert 0.0 <= profile.valence <= 1.0,     "valence out of range"
            assert 0.0 <= profile.energy <= 1.0,      "energy out of range"
            assert 0.0 <= profile.danceability <= 1.0, "danceability out of range"
            assert len(profile.genres) >= 1,           "no genres returned"
            assert profile.tempo_min < profile.tempo_max, "tempo range invalid"

            passed += 1

        except AssertionError as e:
            print(f"  ❌ Assertion failed: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ Error: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_tests())