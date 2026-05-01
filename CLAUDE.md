# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PennyWise — a personal finance tracker monorepo with three containerised subsystems: Flask frontend, Flask REST API backend, and MongoDB database.

## Commands

### Backend (root-level pipenv)

```bash
pipenv install --dev          # install all deps
pipenv run pytest             # run backend tests (path: backend/tests)
pipenv run pytest --cov=backend --cov-report=term-missing
pipenv run pytest backend/tests/test_auth.py::test_login_success   # single test
pipenv run black backend/
pipenv run pylint backend/
python -m backend.app         # run dev server on :5000
```

### Frontend

```bash
pip install -r frontend/requirements.txt pytest pytest-cov responses
cd frontend
pytest tests --cov=app --cov-report=term-missing
python app.py                 # run dev server on :3000
```

### Database seed

```bash
pip install pymongo python-dotenv bcrypt
python database/seed.py       # populates users, transactions, budgets, categories
```

### Full stack (Docker)

```bash
docker compose up --build
docker compose down -v        # also removes the mongo_data volume
```

## Environment Variables

Copy `.env.example` to `.env`. Key vars:

| Variable | Default | Purpose |
|----------|---------|---------|
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection |
| `MONGO_DB_NAME` | `pennywise` | Database name |
| `JWT_SECRET` | `dev-secret-change-in-prod` | Signs JWT tokens |
| `BACKEND_URL` | `http://backend:5000` | Frontend → backend base URL |
| `FLASK_SECRET` | `dev-frontend-secret` | Flask session cookie key |

## Architecture

Three subsystems, each with its own `Dockerfile`:

```
frontend/   (:3000)  — Flask + Jinja2 + Bootstrap; calls backend via requests
backend/    (:5000)  — Flask REST API; talks to MongoDB via pymongo
database/   (:27017) — MongoDB 7 image + init script + seed script
```

### Backend module map

| File | Role |
|------|------|
| `backend/app.py` | App factory; registers all blueprints |
| `backend/config.py` | Env-var config (Mongo URI, collection names, JWT secret) |
| `backend/db.py` | `get_collection()`, `get_users_collection()`, `get_budgets_collection()` |
| `backend/auth.py` | `POST /api/auth/register` and `/login`; bcrypt + PyJWT |
| `backend/transactions.py` | Full CRUD at `/api/transactions` |
| `backend/analytics.py` | `/api/analytics/monthly-summary`, `/spending-trends`, `/top-categories` (pandas/NumPy) |
| `backend/budgets.py` | CRUD + `/api/budgets/status` aggregation pipeline |

### Frontend module map

| File | Role |
|------|------|
| `frontend/app.py` | Flask app factory; all routes; `requests` calls to backend |
| `frontend/templates/` | Jinja2 templates extending `base.html` (Bootstrap 5 + Chart.js) |

### Database

- `database/init/mongo-init.js` — creates collections and indexes on first container start
- `database/seed.py` — idempotent script; inserts demo users, 3 months of transactions, budgets, categories

## Testing approach

### Backend
Tests use hand-rolled fakes and `monkeypatch` to replace `db.get_collection` — no live MongoDB needed. Follow this pattern for new backend tests.

### Frontend
Tests use the `responses` library to mock all HTTP calls to the backend. The `auth_client` fixture pre-loads a session token. No real backend needed.

### Database
Tests use `mongomock` to mock the MongoDB client so `seed.py` can run without a real instance.

## CI/CD

Each subsystem has its own workflow in `.github/workflows/`:

| Workflow | Trigger | Jobs |
|----------|---------|------|
| `backend-ci.yml` | push/PR to `backend/**` | test → build+push → deploy |
| `frontend-ci.yml` | push/PR to `frontend/**` | test → build+push → deploy |
| `database-ci.yml` | push/PR to `database/**` | test-seed → build+push |

All push-to-Docker-Hub and deploy steps run only on `main` merges. Required GitHub Secrets: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `DO_HOST`, `DO_USER`, `DO_SSH_KEY`, `MONGO_URI`, `JWT_SECRET`, `FLASK_SECRET`.
