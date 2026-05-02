"""
Pydantic schemas - source of truth for all request/response shapes.
All backend routers import from here. Member 4 (frontend) references this
file for field names when writing templates and JS.

Do not change field names without a PR and team heads-up (see CLAUDE.md).
"""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------

class AgeRangePreference(BaseModel):
    min: int = Field(..., ge=18, le=99)
    max: int = Field(..., ge=18, le=100)


class ContactInfo(BaseModel):
    phone: Optional[str] = None
    instagram: Optional[str] = None


class TopArtist(BaseModel):
    id: str
    name: str


class AudioFeatures(BaseModel):
    energy: float
    valence: float
    danceability: float
    tempo: float


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    display_name: str = Field(..., min_length=1, max_length=50)
    age: int = Field(..., ge=18, le=100)
    city: str = Field(..., min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    user_id: str


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=50)
    age: Optional[int] = Field(None, ge=18, le=100)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    bio: Optional[str] = Field(None, max_length=300)
    gender: Optional[str] = None
    gender_preference: Optional[str] = None
    age_range_preference: Optional[AgeRangePreference] = None
    contact_info: Optional[ContactInfo] = None


class UserMe(BaseModel):
    """Returned by GET /api/auth/me and GET /api/users/me. Full profile, no secrets."""
    user_id: str
    email: str
    display_name: str
    age: int
    city: str
    bio: Optional[str] = None
    gender: Optional[str] = None
    gender_preference: Optional[str] = None
    age_range_preference: Optional[AgeRangePreference] = None
    photo_url: Optional[str] = None
    contact_info: ContactInfo
    top_genres: list[str]
    top_artists: list[TopArtist]
    audio_features: Optional[AudioFeatures] = None
    is_spotify_connected: bool
    spotify_last_synced: Optional[datetime] = None
    likes_sent_today: int
    created_at: datetime


class UserPublic(BaseModel):
    """
    Returned by GET /api/users/{user_id}.
    photo_url and contact_info are None unless the requester and target are mutually matched.
    Backend controls this - frontend should conditionally render based on null check.
    """
    user_id: str
    display_name: str
    age: int
    city: str
    bio: Optional[str] = None
    gender: Optional[str] = None
    top_genres: list[str]
    top_artists: list[TopArtist]
    photo_url: Optional[str] = None
    contact_info: Optional[ContactInfo] = None


# ---------------------------------------------------------------------------
# Feed
# ---------------------------------------------------------------------------

class FeedProfile(BaseModel):
    """One profile card in the discovery feed. photo_url is always null."""
    user_id: str
    display_name: str
    age: int
    city: str
    bio: Optional[str] = None
    top_genres: list[str]
    top_artists: list[TopArtist]
    match_score: float
    photo_url: Literal[None] = None


class FeedResponse(BaseModel):
    profiles: list[FeedProfile]
    page: int
    has_more: bool


# ---------------------------------------------------------------------------
# Likes
# ---------------------------------------------------------------------------

class LikeResponse(BaseModel):
    matched: bool
    match_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Matches
# ---------------------------------------------------------------------------

class MatchedUser(BaseModel):
    """Minimal user info shown inside a match card. Photo is revealed here."""
    user_id: str
    display_name: str
    age: int
    city: str
    top_genres: list[str]
    photo_url: Optional[str] = None


class MatchResponse(BaseModel):
    match_id: str
    other_user: MatchedUser
    created_at: datetime
    is_new: bool


class MatchListResponse(BaseModel):
    matches: list[MatchResponse]
