# Task Assignments: Vibe

Five members. Each member owns their code, their tests (>=80% coverage), and their Dockerfile/CI where applicable.

| Name | Role |
|---|---|
| Jack Escowitz | Auth + User Profile (Backend) |
| Michael Miao | Spotify Integration + Background Refresh (Backend) |
| Sarah Randhawa | Matching Algorithm + Feed + Likes + Matches (Backend) |
| Angelina Wu | Frontend (Flask) |
| Aryaman Nagpal | Infrastructure (DevOps + MongoDB) |

---

## Jack - Auth + User Profile (Backend)

**Owns:** `backend/app/routers/auth.py`, `backend/app/routers/users.py`, `backend/app/auth.py`, `backend/tests/test_auth.py`, `backend/tests/test_users.py`

**Deliverables:**
- `POST /api/auth/register` - validate input, hash password (bcrypt/passlib), create user doc in MongoDB, return JWT cookie
- `POST /api/auth/login` - verify credentials, return JWT cookie
- `POST /api/auth/logout` - clear cookie
- `GET /api/auth/me` - return current user (no password_hash)
- `GET /api/users/me` - full profile
- `PUT /api/users/me` - update editable profile fields
- `POST /api/users/me/photo` - multipart upload to Cloudinary, save URL to user doc
- `GET /api/users/{user_id}` - public profile; include photo_url + contact_info only if requester and target are mutually matched
- `auth.py` module: `encode_jwt`, `decode_jwt`, `hash_password`, `verify_password`, FastAPI dependency `get_current_user`

**Dependencies:** Needs `database.py` (Aryaman), `models/schemas.py` (define together with team), Cloudinary credentials in env

---

## Michael - Spotify Integration + Background Refresh (Backend)

**Owns:** `backend/app/routers/spotify.py`, `backend/app/services/spotify.py`, `backend/app/services/scheduler.py`, `backend/tests/test_spotify.py`

**Deliverables:**
- `GET /api/spotify/connect` - build Spotify OAuth URL (spotipy), redirect user
- `GET /api/spotify/callback` - exchange auth code for tokens, call `SpotifyService.pull_user_data()`, set `is_spotify_connected=true`, redirect to `/profile/setup`
- `POST /api/spotify/disconnect` - clear tokens, set `is_spotify_connected=false`
- `SpotifyService.pull_user_data(user_id)` - fetch top artists (long-term, limit 50), derive genres from artist genre tags, fetch audio features for top tracks (average across tracks), store all in user doc
- `SpotifyService.refresh_token(user_id)` - use refresh_token to get new access_token, update DB
- APScheduler weekly job: iterate all connected users, call `refresh_token` then `pull_user_data`

**Notes:**
- Use spotipy's `SpotifyOAuth` for the OAuth flow
- Store raw `access_token` and `refresh_token` encrypted at rest is ideal but plain for v1 is acceptable
- Scheduler starts in `backend/app/main.py` startup event

**Dependencies:** Needs `database.py` (Aryaman), Spotify credentials in env

---

## Sarah - Matching Algorithm + Feed + Likes + Matches (Backend)

**Owns:** `backend/app/services/matching.py`, `backend/app/routers/feed.py`, `backend/app/routers/likes.py`, `backend/app/routers/matches.py`, `backend/tests/test_matching.py`, `backend/tests/test_feed.py`, `backend/tests/test_likes.py`, `backend/tests/test_matches.py`

**Deliverables:**
- `matching.py`: pure function `compute_score(user_a: dict, user_b: dict) -> float` (no DB access; testable in isolation)
  - Genre score: Jaccard on `top_genres` sets (weight 0.50)
  - Artist score: Jaccard on `top_artists[].id` sets (weight 0.30)
  - Audio score: 1 - normalized cosine distance of `[energy, valence, danceability, tempo/250]` (weight 0.20); returns 0.5 if either user missing audio features
- `GET /api/feed?page=N` - filter eligible users (city, gender pref, age pref, spotify connected, not self, not already liked); score all candidates; return top 10 for page N sorted by score desc; photo_url always null in response
- `POST /api/likes/{user_id}` - create like doc; check if reverse like exists; if yes create match doc; enforce 50/day limit (check `likes_sent_today`); return `{matched: bool, match_id: string|null}`
- `DELETE /api/likes/{user_id}` - delete like doc
- `GET /api/matches` - return all matches for current user with basic profile info and `is_new` flag
- `PATCH /api/matches/{match_id}/seen` - add current user id to `seen_by`

**Dependencies:** Needs `database.py` (Aryaman)

---

## Angelina - Frontend (Flask)

**Owns:** entire `/frontend/` directory, `frontend/tests/test_routes.py`

**Deliverables:**
- Flask app with routes: `/`, `/login`, `/register`, `/profile/setup`, `/feed`, `/profile/{user_id}`, `/matches`, `/settings`
- Auth check middleware: redirect to `/login` if no JWT cookie on protected routes
- `api_client.py`: helper that calls backend API, forwarding the JWT cookie from the incoming request
- Jinja2 templates for all pages (see Directory Structure in PRD)
- `feed.html` + `feed.js`: fetch `/api/feed`, render profile cards (blurred/no photo), like/skip buttons that call `POST /api/likes/{user_id}` via AJAX
- `matches.html` + `matches.js`: fetch `/api/matches`, mark seen via AJAX
- `profile_detail.html`: fetch `/api/users/{user_id}`; show photo only if matched (backend controls this)
- `settings.html`: show Spotify connect/disconnect button, edit profile form
- CSS: desktop-first, mobile-responsive, music-themed aesthetic

**Notes:**
- The JWT cookie is set by the backend and is httpOnly - the frontend Flask app passes it server-side when making backend calls. For AJAX (client-side JS), cookie is sent automatically if same domain; use `credentials: 'include'` in fetch calls if cross-origin.
- All backend communication goes through `BACKEND_URL` env var (e.g., `http://backend:8000`)

**Dependencies:** Backend endpoints must be stable before full integration; mock responses acceptable for development

---

## Aryaman - Infrastructure (DevOps + MongoDB)

**Owns:** `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `.github/workflows/backend.yml`, `.github/workflows/frontend.yml`, `.env.example`, MongoDB Atlas setup, Digital Ocean setup

**Deliverables:**

**Dockerfiles:**
- `backend/Dockerfile`: Python 3.12 slim base, install requirements, `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`
- `frontend/Dockerfile`: Python 3.12 slim base, install requirements, `CMD ["flask", "--app", "app.main", "run", "--host", "0.0.0.0", "--port", "3000"]`

**docker-compose.yml:** Brings up `mongodb` (official image), `backend` (build from ./backend), `frontend` (build from ./frontend) with correct env var injection and port mappings

**GitHub Actions (both workflows follow this pattern):**
```
on: [push, pull_request] to main
jobs:
  test: pytest --cov=app --cov-fail-under=80
  build-push: docker build + push to Docker Hub (only on push to main)
  deploy: SSH to DO droplet / DO App Platform deploy hook (only on push to main)
```
Secrets to configure in GitHub: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `DO_SSH_KEY` (or DO App Platform token)

**MongoDB Atlas:**
- Create free-tier cluster
- Create `vibe` database with `users`, `likes`, `matches` collections
- Create indexes per data models in PRD
- Create DB user, whitelist DO droplet IP, provide connection string to team

**Digital Ocean:**
- Provision droplet (or App Platform app) for backend and frontend
- Set all env vars from `.env.example` in DO environment

**.env.example:**
```
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/vibe
JWT_SECRET=changeme
JWT_EXPIRY_DAYS=7
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_REDIRECT_URI=http://localhost:8000/api/spotify/callback
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
```

**Dependencies:** Needs Spotify app created at developer.spotify.com (any member can do this) and Cloudinary account (any member)
