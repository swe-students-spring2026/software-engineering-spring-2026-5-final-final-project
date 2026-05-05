# Vibe — Music-First Dating App

Match through music. Photos stay hidden until you both like each other.

---

## Team

| Name | Role |
|---|---|
| Jack Escowitz | Auth + User Profile (Backend) |
| Michael Miao | Spotify Integration + Background Refresh (Backend) |
| Sarah Randhawa | Matching Algorithm + Feed + Likes + Matches (Backend) |
| Angelina Wu | Frontend (Flask) |
| Aryaman Nagpal | Infrastructure (DevOps + MongoDB) |

---

## Setup

```bash
cp .env.example .env
# fill in SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and any other required values
```

**Run everything with Docker:**

```bash
docker-compose up --build
# backend:  http://localhost:8000
# frontend: http://localhost:3000
# mongo:    localhost:27017
```

**Or run subsystems individually (no Docker):**

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
pip install -r requirements.txt
flask --app app.main run --port 3000
```

**Frontend mock mode** (no backend needed — uses fake data):

```bash
# macOS/Linux
cd frontend && MOCK_MODE=true flask --app app.main run --port 3000

# PowerShell
cd frontend; $env:MOCK_MODE="true"; flask --app app.main run --port 3000
```

---

## Tests

Each subsystem has its own `pyproject.toml` that sets the coverage flags. Run from the subsystem root — no extra flags needed.

```bash
# Backend (runs test_database.py + test_spotify.py, ≥80% target)
cd backend
pytest

# Frontend (runs test_routes.py, ≥80% required)
cd frontend
pytest
```

Test files bootstrap their own env vars via `os.environ.setdefault`, so no `.env` file is required to run tests.

**Current coverage status:**

| Subsystem | Tests | Coverage | CI threshold |
|---|---|---|---|
| Backend | 80 passing | 37% | 40% (temp) — raise to 80% as router tests land |
| Frontend | 72 passing | 94% | 80% ✓ |

The backend CI threshold is temporarily set to 40% (`backend.yml` line 34, marked `# CHANGE`). It must be raised back to 80% once tests for the auth, users, feed, likes, matches, and matching routers are written.

---

## CI/CD Pipeline

Defined in [`.github/workflows/`](.github/workflows/).

**Triggers:**
- `pull_request` → `main`: runs tests only
- `push` → `main` (i.e. PR merged): tests → Docker build+push → Digital Ocean deploy

**Backend pipeline** (`backend.yml`):
1. `pytest --cov=app --cov-fail-under=40` (temp)
2. `docker build` → push `vibe-backend:latest` to Docker Hub
3. SSH into DO droplet → `docker pull` + `docker run`

**Frontend pipeline** (`frontend.yml`):
1. `pytest --cov=app --cov-fail-under=80`
2. `docker build` → push `vibe-frontend:latest` to Docker Hub
3. SSH into DO droplet → `docker pull` + `docker run`

**Required GitHub secrets:**

| Secret | Purpose |
|---|---|
| `DOCKERHUB_USERNAME` | Docker Hub account |
| `DOCKERHUB_TOKEN` | Docker Hub access token |
| `DO_HOST` | Digital Ocean droplet IP |
| `DO_USER` | SSH user (e.g. `root`) |
| `DO_SSH_KEY` | Private SSH key for the droplet |

---

## Key URLs (local)

| | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
