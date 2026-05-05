# Final Project

![API CI/CD](https://github.com/swe-students-spring2026/5-final-final_project/actions/workflows/api-service.yml/badge.svg)
![Frontend CI/CD](https://github.com/swe-students-spring2026/5-final-final_project/actions/workflows/web-app.yml/badge.svg)
![Scraper CI/CD](https://github.com/swe-students-spring2026/5-final-final_project/actions/workflows/scraper.yml/badge.svg)

An exercise to practice software development teamwork, database integration, containers, deployment, and CI/CD pipelines.

## Overview

This repository contains three subsystems:

- **`apis/`** — Flask API service (port 8000). Connects to MongoDB and exposes `/health`, `/classes`, and `/chat` (Gemini AI).
- **`frontend/`** — Flask web frontend (port 3000). Proxies class search to the API and serves the UI.
- **`scrapers/`** — CLI scraper that pulls course data from the NYU bulletin and writes to MongoDB or JSON files.

MongoDB runs as a local Docker Compose service with a persistent `mongo_data` volume. The app services reach it with `MONGO_URI=mongodb://mongo:27017/final_project`.
Compose also binds MongoDB to `127.0.0.1:${MONGO_PORT:-27017}` on the host for private import/export commands.

## Team

- [Robin Chen](https://github.com/localhost433)
- [Minho Eune](https://github.com/minhoeune)
- [Jaiden Xu](https://github.com/jbx202)
- [Kyle Chen](https://github.com/KyleC55)

## Docker Hub Repositories

Create the following public repositories on Docker Hub before running CI/CD:

| Subsystem | Docker Hub repo |
|---|---|
| API service | `kylec55/api-service` |
| Frontend | `kylec55/web-app` |
| Scraper | `kylec55/scraper` |


## GitHub Secrets Required

Add these secrets in **Settings → Secrets and variables → Actions** on GitHub:

| Secret | Description |
|---|---|
| `DOCKER_USERNAME` | Your Docker Hub username |
| `DOCKER_PASSWORD` | Your Docker Hub password or access token |
| `GEMINI_API_KEY` | Google Gemini API key (used by the API service) |

## CI/CD Workflows

Each subsystem has its own workflow under `.github/workflows/`:

| File | Triggers on changes to | Pushes image to |
|---|---|---|
| `api-service.yml` | `apis/**` | `DOCKER_USERNAME/api-service:latest` |
| `web-app.yml` | `frontend/**` | `DOCKER_USERNAME/web-app:latest` |
| `scraper.yml` | `scrapers/**` | `DOCKER_USERNAME/scraper:latest` |

Workflows run on every push and pull request to `main`/`master`. The Docker image is only pushed to Docker Hub on a push to `main`/`master` (not on PRs).

## DigitalOcean Deployment

The production app is deployed [here](https://squid-app-3b9ec.ondigitalocean.app/?term=1268&page=1)

Run the stack on a Droplet with Docker Compose. Compose starts four services: `frontend`, `apis`, `scrapers`, and `mongo`.

 MongoDB data is stored in the named `mongo_data` volume on the Droplet, so it survives container rebuilds.

Use the local container URI in `.env`:

```bash
MONGO_URI=mongodb://mongo:27017/final_project
MONGO_DB_NAME=final_project
MONGO_PORT=27017
```

Set `FRONTEND_PUBLIC_URL` to 
`https://squid-app-3b9ec.ondigitalocean.app`.

Add this Google OAuth redirect URI in Google Cloud Console:
`https://squid-app-3b9ec.ondigitalocean.app/auth/google/callback`

## Run Locally with Docker

### Run the API service only

```bash
docker run --rm -p 8000:8000 \
  -e MONGO_URI="mongodb://host.docker.internal:27017/final_project" \
  -e MONGO_DB_NAME=final_project \
  -e GEMINI_API_KEY="your-key" \
  kylec55/api-service:latest
```

### Run the frontend only

```bash
docker run --rm -p 3000:3000 \
  -e API_URL=http://host.docker.internal:8000 \
  kylec55/web-app:latest
```

### Run the scraper

```bash
# List available schools
docker run --rm kylec55/scraper:latest

# Scrape a subject and save to MongoDB
docker run --rm \
  kylec55/scraper:latest \
  python scraper.py --term 1268 --subject CSCI-UA --details \
    --to-mongo "mongodb://host.docker.internal:27017/final_project"
```

### Run the Albert scraper from an already-open browser

Start any Chromium-based browser with remote debugging enabled. Replace `<browser-exe>` with your browser executable path or command:

```bash
"<browser-exe>" --remote-debugging-port=9222 --user-data-dir="/tmp/albert-cdp-profile"
```

Then log in to Albert in that browser window, pass reCAPTCHA, and open the Browse by Subject page. After that, run:

```bash
python3 scrapers/albert_scraper.py --cdp-url http://127.0.0.1:9222
```

This writes scraped classes to `scrapers/classes_example.json` and a coverage summary to `scrapers/classes_example_report.json` so you can verify how many subjects were discovered and visited.

### Run the full local stack with Docker Compose

```bash
cp .env.example .env
# Edit .env and fill in GEMINI_API_KEY, OAuth values, etc.
docker compose up --build
```

Services:
- Frontend: `http://localhost:3000`
- API health check: `http://localhost:8000/health`

To stop:

```bash
docker compose down
```

## Configuration

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

### Environment Variables

| Variable | Used by | Description |
|---|---|---|
| `MONGO_IMAGE_TAG` | `mongo` | MongoDB image tag for the Compose service, default `7` |
| `MONGO_PORT` | `mongo` | Loopback-only host port for private import/export commands, default `27017` |
| `MONGO_URI` | `apis`, `scrapers` | MongoDB connection string; Compose default is `mongodb://mongo:27017/final_project` |
| `MONGO_DB_NAME` | `apis` | Database name, e.g. `final_project` |
| `API_INTERNAL_TOKEN` | `apis`, `frontend` | Shared token the frontend sends to protected API endpoints |
| `GEMINI_API_KEY` | `apis` | Google Gemini API key |
| `GEMINI_MODEL` | `apis` | Default model; used by transcript parsing and as the chat's Balanced-tier fallback (default `gemini-2.5-flash`) |
| `GEMINI_MODEL_FAST` | `apis` | Override for the chat's Fast tier (default `gemini-2.5-flash-lite`) |
| `GEMINI_MODEL_BALANCED` | `apis` | Override for the chat's Balanced tier (defaults to `GEMINI_MODEL`) |
| `GEMINI_MODEL_SMART` | `apis` | Override for the chat's Smart tier (default `gemini-2.5-pro`) |
| `API_URL` | `frontend` | Internal URL of the API service |
| `API_PORT` / `API_INTERNAL_PORT` | `apis` | External / internal port (default `8000`) |
| `FRONTEND_PORT` / `FRONTEND_INTERNAL_PORT` | `frontend` | External / internal port (default `3000`) |
| `PYTHON_IMAGE_TAG` | Docker build | Python base image version, default `3.14` |

## Sanity Check

After deployment, verify the following:

- The deployed app loads successfully at: https://squid-app-3b9ec.ondigitalocean.app/?term=1268&page=1
- The frontend page renders without a server error.
- Google login redirects correctly.
- The Google OAuth callback URL is configured as: `https://squid-app-3b9ec.ondigitalocean.app/auth/google/callback`
- The frontend can reach the backend API.
- The API health check works.
- MongoDB data is kept in the `mongo_data` Docker volume after containers are rebuilt or restarted.
- The scraper service runs without crashing.
- The scraper writes course data into MongoDB.
- Course search returns results
- Logs do not show missing environment variables, MongoDB connection errors, or API connection errors.

## Development Notes

- `apis/app/main.py` — API entrypoint; registers the chat blueprint and the `/classes` route.
- `frontend/app/main.py` — Frontend entrypoint; proxies class search to the API.
- `apis/app/ai/` — Gemini AI client, tool-calling loop, and MongoDB-backed tool handlers (course search, sections, programs, professor lookups).
- `scrapers/scraper.py` — Full scraper CLI; run with `--help` to see all options.
- Each subsystem has its own `Dockerfile` and runtime `requirements.txt`; API and frontend tests use `requirements-dev.txt`.
