from pydantic import BaseModel, Field
from typing import Optional


# ── Inbound ──────────────────────────────────────────────────────────────────

class WeatherData(BaseModel):
    temp: float = Field(..., description="Temperature in Celsius")
    condition: str = Field(..., description="e.g. 'drizzle', 'clear sky', 'thunderstorm'")
    humidity: int = Field(..., description="Relative humidity 0–100")
    city: Optional[str] = Field(None, description="City name for display")


class PredictRequest(BaseModel):
    mood: str = Field(..., description="Free-text or picker-selected mood string")
    weather: WeatherData
    user_id: Optional[str] = Field(None, description="Spotify user ID for session logging")
    limit: int = Field(default=20, ge=1, le=50, description="Number of tracks to return")


# ── Internal ─────────────────────────────────────────────────────────────────

class AudioProfile(BaseModel):
    valence: float = Field(..., ge=0.0, le=1.0)
    energy: float = Field(..., ge=0.0, le=1.0)
    danceability: float = Field(..., ge=0.0, le=1.0)
    tempo_min: int
    tempo_max: int
    genres: list[str]
    reasoning: str


# ── Outbound ─────────────────────────────────────────────────────────────────

class Track(BaseModel):
    uri: str
    name: str
    artist: str
    album: str
    preview_url: Optional[str]
    external_url: str
    valence: Optional[float] = None
    energy: Optional[float] = None


class PredictResponse(BaseModel):
    tracks: list[Track]
    profile: AudioProfile
    session_id: Optional[str] = None


# ── Feedback ─────────────────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    session_id: str
    track_uri: str
    rating: int = Field(..., ge=1, le=5, description="1 = bad fit, 5 = perfect")


class FeedbackResponse(BaseModel):
    saved: bool
    message: str


# ── Weather proxy ─────────────────────────────────────────────────────────────

class WeatherResponse(BaseModel):
    temp: float
    condition: str
    humidity: int
    city: str
    icon: str
