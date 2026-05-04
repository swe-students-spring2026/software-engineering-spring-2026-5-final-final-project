# Vibe — Music-First Dating App

Match through music. Photos stay hidden until you both like each other.

An exercise in software development teamwork, containerization, CI/CD pipelines, and subsystem communication. See [instructions](./instructions.md) for assignment details.

---
## Team

| Name | Role |
|---|---|
| Jack Escowitz | Auth + User Profile (Backend) |
| Michael Miao | Spotify Integration + Background Refresh (Backend) |
| Sarah Randhawa | Matching Algorithm + Feed + Likes + Matches (Backend) |
| Angelina Wu | Frontend (Flask) |
| Aryaman Nagpal | Infrastructure (DevOps + MongoDB) |

## Architecture

| Subsystem | Stack | Port |
|---|---|---|
| Backend | FastAPI + motor (async MongoDB) | 8000 |
| Frontend | Flask + Jinja2 + vanilla JS | 3000 |
| Database | MongoDB | 27017 |

---

## Running the full stack (Docker)

```bash
cp .env.example .env
# Fill in all values in .env

docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

---

## Frontend

### Quick start (standalone)

```bash
cd frontend
pip install -r requirements.txt
flask --app app.main run --port 3000
```

The frontend expects the backend to be running at `BACKEND_URL` (default: `http://localhost:8000`).

### Mock mode (no backend needed)

Set `MOCK_MODE=true` to run against hardcoded fake data — no backend or database required:

```bash
cd frontend
MOCK_MODE=true flask --app app.main run --port 3000
```

On Windows PowerShell:

```powershell
$env:MOCK_MODE="true"
flask --app app.main run --port 3000
```

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `BACKEND_URL` | `http://localhost:8000` | URL of the FastAPI backend |
| `MOCK_MODE` | `false` | Return hardcoded data instead of calling the backend |
| `FLASK_SECRET_KEY` | `dev-secret-change-me` | Flask session secret — change in production |

### Pages

| Route | Description |
|---|---|
| `/` | Redirects to `/feed` if logged in, otherwise `/login` |
| `/login` | Sign in |
| `/register` | Create account |
| `/profile/setup` | Fill in bio, gender, age range, photo after connecting Spotify |
| `/feed` | Swipe through ranked profiles |
| `/profile/<user_id>` | View a profile (photo only visible after mutual match) |
| `/matches` | All mutual matches with contact info |
| `/settings` | Edit profile, connect/disconnect Spotify |

### Running tests

```bash
cd frontend
pytest --cov=app --cov-report=term-missing
```

Coverage must be ≥ 80%. Current coverage: **93%**.

---

## Backend

### Quick start (standalone)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Running tests

```bash
cd backend
pytest --cov=app --cov-report=term-missing
```

---

## Environment variables (full list)

Copy `.env.example` to `.env` and fill in values:

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

---

