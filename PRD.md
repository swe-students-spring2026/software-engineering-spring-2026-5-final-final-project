# PRD: Vibe - Music-First Dating App

## Overview

Vibe is a web-based dating/matchmaking app where music taste is the primary basis for matching. Users connect their Spotify account and are shown a ranked feed of potential matches based on genre overlap, artist overlap, and audio feature compatibility. Profile photos are hidden by default and only unlocked after a mutual like.

---

## Problem Statement

Most dating apps lead with photos and reduce compatibility to surface-level filters. Vibe inverts this: music taste is a proven proxy for personality and lifestyle. By leading with what you listen to instead of what you look like, Vibe filters for genuine compatibility before physical attraction enters the picture.

---

## Users

- **Primary:** Young adults (18-30) who are active Spotify users

---

## System Architecture

| Subsystem | Language/Stack | Port | Role |
|---|---|---|---|
| **Backend** | Python / FastAPI | 8000 | REST API, auth, Spotify integration, matching algorithm |
| **Frontend** | Python / Flask + Jinja2 + vanilla JS | 3000 | Web UI (server-rendered + AJAX) |
| **Database** | MongoDB | 27017 | Persistent storage |

Each custom subsystem (Backend, Frontend) has its own:
- Subdirectory (`/backend/`, `/frontend/`)
- `Dockerfile` with image published to Docker Hub
- GitHub Actions workflow triggered on push/PR to `main`
- Unit tests with >= 80% code coverage

---

## Tech Stack Decisions

| Concern | Choice | Reason |
|---|---|---|
| Backend framework | FastAPI | Async, auto-generated docs, Pydantic models |
| Frontend framework | Flask + Jinja2 | Simplest Python-served HTML; AJAX for interactive parts |
| MongoDB driver | motor (async) | Matches FastAPI async model |
| Auth | JWT via PyJWT | Stored in httpOnly cookie; 7-day expiry |
| Spotify SDK | spotipy | Official Python wrapper |
| Photo storage | Cloudinary | Free tier; simple Python SDK; no self-hosted infra |
| Password hashing | bcrypt (passlib) | Standard |
| Background jobs | APScheduler (in-process) | Weekly Spotify refresh; no separate worker infra needed for v1 |
| Local dev orchestration | docker-compose | Brings up all three services together |

---

## Directory Structure

```
/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── config.py          # Settings from env vars (pydantic BaseSettings)
│   │   ├── database.py        # Motor client + collection accessors
│   │   ├── auth.py            # JWT encode/decode, password hashing, auth dependency
│   │   ├── routers/
│   │   │   ├── auth.py        # /api/auth/*
│   │   │   ├── users.py       # /api/users/*
│   │   │   ├── spotify.py     # /api/spotify/*
│   │   │   ├── feed.py        # /api/feed
│   │   │   ├── likes.py       # /api/likes/*
│   │   │   └── matches.py     # /api/matches/*
│   │   ├── services/
│   │   │   ├── spotify.py     # Spotify API calls, token refresh
│   │   │   ├── matching.py    # Match score computation
│   │   │   └── scheduler.py   # APScheduler weekly refresh job
│   │   └── models/
│   │       └── schemas.py     # Pydantic request/response schemas
│   ├── tests/
│   │   ├── test_auth.py
│   │   ├── test_users.py
│   │   ├── test_spotify.py
│   │   ├── test_feed.py
│   │   ├── test_likes.py
│   │   ├── test_matches.py
│   │   └── test_matching.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml         # pytest + coverage config
│
├── frontend/
│   ├── app/
│   │   ├── main.py            # Flask app entry point
│   │   ├── config.py          # BACKEND_URL and other env vars
│   │   ├── routes.py          # Page routes
│   │   ├── api_client.py      # Helper to proxy/call backend API
│   │   ├── templates/
│   │   │   ├── base.html
│   │   │   ├── login.html
│   │   │   ├── register.html
│   │   │   ├── profile_setup.html
│   │   │   ├── feed.html
│   │   │   ├── profile_detail.html
│   │   │   ├── matches.html
│   │   │   └── settings.html
│   │   └── static/
│   │       ├── css/style.css
│   │       └── js/
│   │           ├── feed.js    # Like/skip actions, pagination
│   │           └── matches.js
│   ├── tests/
│   │   └── test_routes.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
│
├── .github/
│   └── workflows/
│       ├── backend.yml
│       └── frontend.yml
│
├── docker-compose.yml
├── .env.example
├── CLAUDE.md
└── README.md
```

---

## Environment Variables

All secrets live in a `.env` file (not committed). See `.env.example` for the template.

| Variable | Used By | Description |
|---|---|---|
| `MONGODB_URI` | Backend | Full MongoDB connection string |
| `JWT_SECRET` | Backend | Secret key for signing JWTs |
| `JWT_EXPIRY_DAYS` | Backend | JWT lifetime in days (default: 7) |
| `SPOTIFY_CLIENT_ID` | Backend | Spotify app client ID |
| `SPOTIFY_CLIENT_SECRET` | Backend | Spotify app client secret |
| `SPOTIFY_REDIRECT_URI` | Backend | OAuth callback URL (e.g. `http://localhost:8000/api/spotify/callback`) |
| `CLOUDINARY_CLOUD_NAME` | Backend | Cloudinary cloud name |
| `CLOUDINARY_API_KEY` | Backend | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | Backend | Cloudinary API secret |
| `BACKEND_URL` | Frontend | Internal URL of backend (e.g. `http://backend:8000`) |
| `FRONTEND_URL` | Backend | Frontend URL for CORS whitelist |

---

## Data Models

### MongoDB Collections and Indexes

#### `users`
```json
{
  "_id": "ObjectId",
  "email": "string (unique)",
  "password_hash": "string",
  "display_name": "string",
  "age": "int",
  "city": "string",
  "bio": "string | null",
  "gender": "string | null",
  "gender_preference": "string | null",
  "age_range_preference": { "min": "int", "max": "int" },
  "photo_url": "string | null",
  "contact_info": { "phone": "string | null", "instagram": "string | null" },
  "spotify": {
    "access_token": "string | null",
    "refresh_token": "string | null",
    "top_artists": [{ "id": "string", "name": "string" }],
    "top_genres": ["string"],
    "audio_features": { "energy": "float", "valence": "float", "danceability": "float", "tempo": "float" },
    "last_synced": "datetime | null"
  },
  "is_spotify_connected": "bool",
  "likes_sent_today": "int",
  "likes_reset_at": "datetime",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

Indexes: `email` (unique), `city`, `is_spotify_connected`

#### `likes`
```json
{
  "_id": "ObjectId",
  "from_user_id": "ObjectId",
  "to_user_id": "ObjectId",
  "created_at": "datetime"
}
```

Indexes: `(from_user_id, to_user_id)` (unique), `to_user_id`

#### `matches`
```json
{
  "_id": "ObjectId",
  "user_ids": ["ObjectId", "ObjectId"],
  "seen_by": ["ObjectId"],
  "created_at": "datetime"
}
```

Indexes: `user_ids`

---

## API Contract (Backend - FastAPI)

All endpoints are prefixed `/api`. Auth-required endpoints expect a JWT in an httpOnly cookie named `vibe_token`. Error responses follow `{ "detail": "message" }`.

### Auth

| Method | Path | Auth | Request Body | Response |
|---|---|---|---|---|
| POST | `/api/auth/register` | No | `{email, password, display_name, age, city}` | `{user_id}` + sets cookie |
| POST | `/api/auth/login` | No | `{email, password}` | `{user_id}` + sets cookie |
| POST | `/api/auth/logout` | No | - | clears cookie |
| GET | `/api/auth/me` | Yes | - | full user object (no password_hash) |

### Users

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/users/me` | Yes | Full profile |
| PUT | `/api/users/me` | Yes | Body: any subset of editable fields (display_name, age, city, bio, gender, gender_preference, age_range_preference, contact_info) |
| POST | `/api/users/me/photo` | Yes | Multipart form upload; stores to Cloudinary; saves URL |
| GET | `/api/users/{user_id}` | Yes | Public fields only; adds photo_url + contact_info if mutually matched |

### Spotify

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/spotify/connect` | Yes | Redirects to Spotify OAuth authorization URL |
| GET | `/api/spotify/callback` | Yes (via state param) | Exchanges code for tokens; pulls initial data; sets `is_spotify_connected=true` |
| POST | `/api/spotify/disconnect` | Yes | Clears tokens; sets `is_spotify_connected=false` (hides from feed) |

### Feed

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/feed` | Yes (Spotify required) | Query params: `page=1` (0-indexed, 10 per page). Returns ranked profiles. Excludes self, already-liked users, and users outside preferences. |

Feed response per profile:
```json
{
  "user_id": "string",
  "display_name": "string",
  "age": "int",
  "city": "string",
  "bio": "string | null",
  "top_genres": ["string"],
  "top_artists": [{"name": "string"}],
  "match_score": "float",
  "photo_url": null
}
```
`photo_url` is always `null` in feed responses (only revealed on match).

### Likes

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/likes/{user_id}` | Yes | Creates like; checks for mutual like; creates Match if mutual. Returns `{matched: bool, match_id: string|null}`. Enforces 50 likes/day limit. |
| DELETE | `/api/likes/{user_id}` | Yes | Removes like (does not delete match if one exists) |

### Matches

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/matches` | Yes | Returns all matches; includes `is_new` flag if current user is not in `seen_by` |
| PATCH | `/api/matches/{match_id}/seen` | Yes | Adds current user to `seen_by` |

---

## Matching Algorithm

Encapsulated in `backend/app/services/matching.py`. Must be independently testable with no database dependency.

```
score(user_a, user_b) = 0.50 * genre_score + 0.30 * artist_score + 0.20 * audio_score
```

- **genre_score**: Jaccard similarity of `top_genres` sets
  - `|A ∩ B| / |A ∪ B|`; returns 0.0 if both sets are empty
- **artist_score**: Jaccard similarity of top artist ID sets (same formula)
- **audio_score**: 1 - normalized cosine distance of `[energy, valence, danceability, tempo]` vectors
  - Normalize tempo to [0,1] by dividing by 250 before computing distance
  - Returns 0.5 (neutral) if either user has no audio features

Score range: [0.0, 1.0]. Scores are NOT persisted; recomputed on each feed request.

---

## Functional Requirements (Resolved)

### Decisions on Open Questions

| Question | Decision |
|---|---|
| Match score weights | Genre 50%, Artist 30%, Audio 20% |
| Location matching | Strict city string match (case-insensitive) for v1 |
| Like rate limit | 50 likes/day per user; resets at midnight UTC |
| Spotify disconnect | User is hidden from feed (`is_spotify_connected=false`); they see a reconnect prompt |
| Feed < 10 results | Return however many eligible users exist (can be 0) |
| Photo storage | Cloudinary (free tier) |
| Session management | JWT in httpOnly cookie; 7-day expiry; no refresh tokens in v1 |

### Authentication Flow
1. Register -> JWT cookie set -> redirect to Spotify connect
2. Spotify connect -> OAuth redirect -> callback stores tokens + pulls data -> redirect to profile setup
3. Profile setup (fill in remaining fields, upload photo) -> redirect to feed

### Discovery Feed
- Filter: same city (case-insensitive), gender preference (if set), age range preference (if set), Spotify connected, not already liked by current user, not current user
- Rank by match score descending
- Page size: 10
- Photo is always hidden in feed and profile detail views until mutual match

### Weekly Refresh Job
- APScheduler `IntervalTrigger(weeks=1)` started on app startup
- For each user where `is_spotify_connected=true`:
  1. Refresh Spotify access token via refresh_token
  2. Re-pull top artists, top genres, audio features
  3. Update `spotify.last_synced`
- Match scores are recomputed on feed request, not stored, so no recomputation step needed

---

## Frontend Routes (Flask)

| Route | Template | Notes |
|---|---|---|
| `GET /` | redirect to `/feed` or `/login` | Based on auth cookie |
| `GET /login` | login.html | |
| `GET /register` | register.html | |
| `GET /profile/setup` | profile_setup.html | After Spotify connect |
| `GET /feed` | feed.html | Auth required; JS fetches `/api/feed` |
| `GET /profile/{user_id}` | profile_detail.html | Auth required; JS fetches `/api/users/{user_id}` |
| `GET /matches` | matches.html | Auth required; JS fetches `/api/matches` |
| `GET /settings` | settings.html | Auth required |

The Flask frontend proxies the JWT cookie through to the backend API on server-side requests. For client-side AJAX, the browser sends the cookie automatically (same-site or CORS-credentialed).

---

## CI/CD Pipelines (GitHub Actions)

Each workflow file lives at `.github/workflows/{subsystem}.yml` and triggers on `push` or `pull_request` to `main`.

Workflow steps (both subsystems follow same pattern):

1. **Test**: `pytest --cov=app --cov-fail-under=80`
2. **Build**: `docker build -t {dockerhub-user}/vibe-{subsystem}:${{ github.sha }} .`
3. **Push**: Push image to Docker Hub (credentials in GitHub secrets)
4. **Deploy**: SSH into Digital Ocean droplet, pull new image, restart container (or use DO App Platform deploy hook)

GitHub Secrets needed per subsystem: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `DO_SSH_KEY` (or `DO_APP_ID` + `DO_API_TOKEN` for App Platform).

---

## Non-Functional Requirements

- Web only; desktop-first, mobile-responsive
- No real-time features (no WebSocket)
- No in-app messaging
- All custom subsystems containerized
- Test coverage >= 80% per subsystem
- Spotify required; app shows reconnect prompt if disconnected

---

## Out of Scope (v1)

- Mobile app
- Real-time chat or notifications
- Blocking / reporting users
- Email notifications
- Premium tier
- Letterboxd or other platform integrations
