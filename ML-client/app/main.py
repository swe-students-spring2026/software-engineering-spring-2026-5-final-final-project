from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from schemas import (
    PredictRequest,
    PredictResponse,
    FeedbackRequest,
    FeedbackResponse,
    WeatherResponse,
)
from mood_parser import parse_mood
from recommender import get_tracks
from weather import fetch_weather, fetch_weather_by_city
from database import save_session, save_feedback

app = FastAPI(
    title="Mood Music ML Service",
    description="Weather + mood → Spotify playlist recommendations",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ── Weather proxy ─────────────────────────────────────────────────────────────

@app.get("/weather", response_model=WeatherResponse)
async def get_weather_by_coords(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
):
    """
    The frontend calls this with the browser's geolocation coords.
    Returns structured weather the UI can display before the user picks a mood.
    """
    try:
        return await fetch_weather(lat, lon)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Weather API error: {e}")


@app.get("/weather/city", response_model=WeatherResponse)
async def get_weather_by_city(city: str = Query(..., description="City name")):
    """Fallback: fetch weather by city name if geolocation is unavailable."""
    try:
        return await fetch_weather_by_city(city)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Weather API error: {e}")


# ── Core prediction ───────────────────────────────────────────────────────────

@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
    """
    Main endpoint. Accepts mood text + weather, returns a ranked track list.

    Flow:
      1. Claude API  → parse mood + weather into audio feature profile
      2. Spotify API → fetch recommendations matching that profile
      3. MongoDB     → persist session for feedback/analytics
    """
    # Step 1 — mood + weather → audio profile via Claude
    try:
        profile = await parse_mood(req.mood, req.weather)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Mood parsing error: {e}")

    # Step 2 — audio profile → track list via Spotify
    try:
        tracks = await get_tracks(profile, limit=req.limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Spotify error: {e}")

    if not tracks:
        raise HTTPException(
            status_code=404,
            detail="No tracks found for this mood/weather combination. Try a different mood.",
        )

    # Step 3 — persist session to MongoDB
    session_id = None
    try:
        session_id = save_session(
            user_id=req.user_id,
            mood=req.mood,
            weather=req.weather.model_dump(),
            profile=profile.model_dump(),
            tracks=[t.model_dump() for t in tracks],
        )
    except Exception:
        # Non-fatal — don't fail the request if DB is unavailable
        pass

    return PredictResponse(
        tracks=tracks,
        profile=profile,
        session_id=session_id,
    )


# ── Feedback ──────────────────────────────────────────────────────────────────

@app.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(req: FeedbackRequest):
    """
    User rates a track (1–5 stars). Stored in MongoDB for future model tuning.
    """
    try:
        saved = save_feedback(req.session_id, req.track_uri, req.rating)
        return FeedbackResponse(
            saved=saved,
            message="Thanks for your feedback!" if saved else "Could not save feedback.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feedback error: {e}")
