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
# fill in .env
```

**Run everything with Docker:**

```bash
docker-compose up --build
```

**Or run subsystems individually:**

```bash
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

cd frontend && pip install -r requirements.txt
flask --app app.main run --port 3000
```

**Frontend mock mode** (no backend needed — uses fake data):

```bash
cd frontend
MOCK_MODE=true flask --app app.main run --port 3000
# PowerShell: $env:MOCK_MODE="true"; flask --app app.main run --port 3000
```

---

## Tests

```bash
cd backend  && pytest --cov=app --cov-report=term-missing
cd frontend && pytest --cov=app --cov-report=term-missing
```

Coverage must be ≥ 80% per subsystem.

---

## Key URLs (local)

| | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
