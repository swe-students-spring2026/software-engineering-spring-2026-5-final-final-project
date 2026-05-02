# CLAUDE.md - Vibe Project

## Project

Vibe is a music-first dating app. Users connect Spotify and are matched based on genre/artist/audio overlap. Photos are hidden until mutual match.

**Class assignment:** CSCI-UA 0474, NYU. Graded on: containerization, CI/CD (GitHub Actions -> Docker Hub -> Digital Ocean), unit tests >=80% coverage.

See `PRD.md` for full spec. See `TASKS.md` for member ownership.

---

## Architecture

| Subsystem | Stack | Port | Directory |
|---|---|---|---|
| Backend | FastAPI + motor (async MongoDB) | 8000 | `/backend/` |
| Frontend | Flask + Jinja2 + vanilla JS | 3000 | `/frontend/` |
| Database | MongoDB | 27017 | Managed (Atlas or docker-compose) |

---

## Git Workflow

**Branch naming:** `{firstname}/{short-description}` - e.g., `jack/auth-endpoints`, `sarah/matching-algorithm`

**Rules:**
- Never commit directly to `main`
- Open a PR for every change; at least one other member must approve before merge
- CI must be green before merge (tests + coverage)
- Commit message format: `[firstname] short description` - e.g., `[jack] add register endpoint`

**Shared files** - changes to these require a PR with explicit team heads-up before opening (post in group chat first):
- `backend/app/models/schemas.py` - the schema contract; all members depend on it
- `backend/app/main.py` - router registration and startup events
- `backend/app/database.py` - collection accessors
- `docker-compose.yml`

**Dependency order for unblocking work:**
1. Aryaman commits `docker-compose.yml`, `.env.example`, both `Dockerfile`s first
2. Jack commits `auth.py` + `/api/auth/*` before any other backend member writes code that calls `get_current_user`
3. Michael and Sarah can work in parallel once Jack's auth is merged
4. Angelina can develop against mock JSON responses until backend endpoints are stable; switch to real API once merged

---

## Tech Stack

- **Backend:** FastAPI, motor, PyJWT, passlib[bcrypt], spotipy, cloudinary, APScheduler
- **Frontend:** Flask, Jinja2, requests (for server-side backend calls)
- **Database:** MongoDB (motor driver in backend)
- **Auth:** JWT in httpOnly cookie named `vibe_token`; 7-day expiry
- **Photos:** Cloudinary
- **Background jobs:** APScheduler (in-process, weekly Spotify refresh)

---

## Running Locally

```bash
cp .env.example .env
# fill in .env values

docker-compose up --build
# backend: http://localhost:8000
# frontend: http://localhost:3000
# mongo: localhost:27017
```

Running a subsystem standalone (without Docker):

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

cd frontend
pip install -r requirements.txt
flask --app app.main run --port 3000
```

---

## Testing

```bash
cd backend
pytest --cov=app --cov-report=term-missing

cd frontend
pytest --cov=app --cov-report=term-missing
```

Coverage must be >=80% per subsystem. CI will fail below this threshold.

Use `pytest-asyncio` for async FastAPI route tests. Use `mongomock-motor` or `unittest.mock` to mock MongoDB in tests (do not require a live DB to run tests).

---

## Key Conventions

### Backend (FastAPI)

- All routes are under `/api/` prefix
- Auth dependency: `get_current_user` from `app/auth.py` - inject via `Depends(get_current_user)`
- DB access: use motor collections from `app/database.py`, never instantiate MongoClient directly in routes
- All config (env vars): use `app/config.py` (pydantic `BaseSettings`) - never read `os.environ` directly in routes or services
- Pydantic schemas in `app/models/schemas.py` for all request/response bodies
- Matching algorithm in `app/services/matching.py` is pure (no I/O); keep it that way for testability

### Frontend (Flask)

- Auth check: decorator or `before_request` hook - redirect to `/login` if no `vibe_token` cookie on protected routes
- All backend calls go through `app/api_client.py` - pass the JWT cookie forward on server-side calls; never hardcode the backend URL
- JS fetch calls: use `credentials: 'include'` to send the cookie cross-origin
- `photo_url` from the feed API is always null - don't show a photo placeholder in feed cards

### Both Subsystems

- Do not commit `.env` - only `.env.example`
- Python 3.12
- `pyproject.toml` at the subsystem root for pytest and coverage config

---

## Data Models (Quick Reference)

```
users: _id, email, password_hash, display_name, age, city, bio, gender,
       gender_preference, age_range_preference{min,max}, photo_url,
       contact_info{phone,instagram}, spotify{access_token,refresh_token,
       top_artists[{id,name}],top_genres[],audio_features{energy,valence,
       danceability,tempo},last_synced}, is_spotify_connected,
       likes_sent_today, likes_reset_at, created_at, updated_at

likes: _id, from_user_id, to_user_id, created_at

matches: _id, user_ids[2], seen_by[], created_at
```

---

## Match Score Formula

```python
score = 0.50 * jaccard(genres_a, genres_b) \
      + 0.30 * jaccard(artist_ids_a, artist_ids_b) \
      + 0.20 * audio_similarity(features_a, features_b)
```

Audio similarity: `1 - cosine_distance([energy, valence, danceability, tempo/250])`. Returns 0.5 if either user has no audio features.

---

## API Quick Reference

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | /api/auth/register | No | Create account + set cookie |
| POST | /api/auth/login | No | Login + set cookie |
| POST | /api/auth/logout | No | Clear cookie |
| GET | /api/auth/me | Yes | Current user |
| GET | /api/users/me | Yes | Full profile |
| PUT | /api/users/me | Yes | Update profile |
| POST | /api/users/me/photo | Yes | Upload photo (multipart) |
| GET | /api/users/{id} | Yes | Public profile (+ private if matched) |
| GET | /api/spotify/connect | Yes | Redirect to Spotify OAuth |
| GET | /api/spotify/callback | Yes | OAuth callback |
| POST | /api/spotify/disconnect | Yes | Disconnect Spotify |
| GET | /api/feed | Yes | Ranked feed (10 per page, ?page=N) |
| POST | /api/likes/{user_id} | Yes | Like user; returns {matched, match_id} |
| DELETE | /api/likes/{user_id} | Yes | Unlike |
| GET | /api/matches | Yes | All matches with is_new flag |
| PATCH | /api/matches/{id}/seen | Yes | Mark match seen |

---

## HTTP Status Codes

| Situation | Code |
|---|---|
| Success (read/update) | 200 |
| Created (register, like, match) | 201 |
| Bad input / validation error | 422 (FastAPI default for Pydantic) |
| Wrong password / bad credentials | 401 |
| Missing or expired JWT | 401 |
| Authenticated but forbidden (e.g., accessing another user's private data without match) | 403 |
| Resource not found | 404 |
| Duplicate email on register | 409 |
| Like rate limit exceeded (50/day) | 429 |
| Spotify not connected when feed is requested | 403 (with `detail: "spotify_required"`) |

---

## Spec Details (Resolved Gaps)

### Cookie Behavior

| Environment | `SameSite` | `Secure` | Notes |
|---|---|---|---|
| Local dev | `Lax` | `False` | Frontend (3000) and backend (8000) are same host, different ports - `Lax` is sufficient for server-side; AJAX needs `credentials: 'include'` + CORS |
| Production | `None` | `True` | Different domains require `None`; must be HTTPS |

Backend must set `Access-Control-Allow-Origin: {FRONTEND_URL}` and `Access-Control-Allow-Credentials: true`. Never use `*` for origin when credentials are involved.

### Spotify OAuth State Param

The `/api/spotify/connect` endpoint is auth-required (user is already logged in). Encode the user's `user_id` into the `state` param as a short-lived signed JWT (sign with `JWT_SECRET`, 10-minute expiry). On `/api/spotify/callback`, verify and decode `state` to retrieve `user_id` - no server-side session needed.

### Feed Response Envelope

```json
{
  "profiles": [...],
  "page": 0,
  "has_more": true
}
```

`page` is 0-indexed. `has_more` is `true` if there are more eligible users beyond the current page.

### Spotify Data Pull Details

When pulling user data via spotipy:
- **Top artists:** `time_range=long_term`, `limit=50`
- **Top genres:** flatten and deduplicate `artist.genres` across all top artists
- **Audio features:** fetch top 50 tracks (`time_range=medium_term`), call `audio_features()` on all track IDs, average `energy`, `valence`, `danceability`, `tempo` across tracks (skip null responses)

### Photo Upload

- Accepted formats: JPEG, PNG, WebP
- Max file size: 5MB (enforce in FastAPI before uploading to Cloudinary)
- Cloudinary folder: `vibe/profile_photos/{user_id}`
- Replace existing photo by uploading with `public_id=user_id` (Cloudinary will overwrite)
