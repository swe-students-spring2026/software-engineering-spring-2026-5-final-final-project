# NYU Course Planner

![API CI/CD](https://github.com/swe-students-spring2026/5-final-final_project/actions/workflows/api-service.yml/badge.svg)
![Frontend CI/CD](https://github.com/swe-students-spring2026/5-final-final_project/actions/workflows/web-app.yml/badge.svg)
![Scraper CI/CD](https://github.com/swe-students-spring2026/5-final-final_project/actions/workflows/scraper.yml/badge.svg)

NYU Course Planner is a full-stack web app that helps NYU students search courses, compare sections, build a semester schedule, track graduation progress, and get AI-assisted course planning advice. The app combines NYU course data, program requirements, student profile information, transcript parsing, professor lookup, and a Gemini-powered course assistant into one planning workspace.

The production app is deployed here: https://squid-app-3b9ec.ondigitalocean.app/?term=1268&page=1

## Features

- Search NYU courses by term, title, course code, subject, school, component, status, or instructor.
- Add lecture, recitation, lab, and other section combinations to a visual schedule.
- Export selected courses as an `.ics` calendar file for Google Calendar, Apple Calendar, or Outlook.
- Browse undergraduate programs and degree requirement tables.
- Track graduation progress against selected major and minor requirements.
- Create an NYU-only account with email/password or Google OAuth.
- Save profile details, selected programs, completed courses, current courses, and test credits.
- Upload an unofficial transcript PDF and extract completed/current courses.
- Search professor profiles and enrich course results with Rate My Professors data when available.
- Ask the AI Course Assistant for schedule ideas and course recommendations grounded in database-backed tools.

## Team

- [Robin Chen](https://github.com/localhost433)
- [Minho Eune](https://github.com/minhoeune)
- [Jaiden Xu](https://github.com/jbx202)
- [Kyle Chen](https://github.com/KyleC55)

## Architecture

This monorepo contains three custom Python subsystems plus MongoDB:

| Subsystem | Path | Default port | Description |
|---|---|---:|---|
| Frontend | `frontend/` | 3000 | Flask/Jinja web app, login flow, UI pages, and frontend API proxies |
| API service | `apis/` | 8000 | Flask REST API for courses, users, transcripts, programs, professors, and AI chat |
| Scraper worker | `scrapers/` | N/A | CLI and long-running scraper jobs for NYU Bulletin, Albert imports, and MongoDB loading |
| Database | Docker service `mongo` | 27017 | MongoDB database with persistent Docker volume storage |

Docker Compose starts `frontend`, `apis`, `scrapers`, and `mongo`. The application services talk to MongoDB through `MONGO_URI=mongodb://mongo:27017/final_project`, and the host machine can access MongoDB privately at `127.0.0.1:${MONGO_PORT:-27017}`.

## Docker Images

The CI/CD pipelines build and publish each custom subsystem image to Docker Hub:

| Subsystem | Docker Hub image |
|---|---|
| API service | [`kylec55/api-service`](https://hub.docker.com/r/kylec55/api-service) |
| Frontend | [`kylec55/web-app`](https://hub.docker.com/r/kylec55/web-app) |
| Scraper | [`kylec55/scraper`](https://hub.docker.com/r/kylec55/scraper) |

## Repository Layout

```text
.
|-- apis/                  # Flask API service and API tests
|-- frontend/              # Flask web app, templates, static assets, and frontend tests
|-- scrapers/              # Course/program scrapers and MongoDB loading tools
|-- tests/                 # Root-level scraper tests
|-- docker-compose.yml     # Local and droplet service orchestration
|-- .env.example           # Example local configuration
`-- README.md
```

## Configuration

Copy the example environment file before running locally:

```bash
cp .env.example .env
```

Then fill in the values that are specific to your machine and accounts.

| Variable | Used by | Required | Description |
|---|---|---|---|
| `MONGO_IMAGE_TAG` | `mongo` | No | MongoDB image tag, default `7` |
| `MONGO_PORT` | `mongo` | No | Loopback-only host port for private import/export commands, default `27017` |
| `MONGO_URI` | `apis`, `scrapers` | Yes | MongoDB connection string; Compose default is `mongodb://mongo:27017/final_project` |
| `MONGO_DB_NAME` | `apis`, `scrapers` | Yes | MongoDB database name, usually `final_project` |
| `API_INTERNAL_TOKEN` | `apis`, `frontend` | Yes | Shared secret used by the frontend for protected API calls |
| `GEMINI_API_KEY` | `apis` | Yes | Google Gemini API key for AI chat and transcript fallback parsing |
| `GEMINI_MODEL` | `apis` | No | Default Gemini model, default `gemini-2.5-flash` |
| `GEMINI_MODEL_FAST` | `apis` | No | Fast chat model override, default `gemini-2.5-flash-lite` |
| `GEMINI_MODEL_BALANCED` | `apis` | No | Balanced chat model override; falls back to `GEMINI_MODEL` |
| `GEMINI_MODEL_SMART` | `apis` | No | Smart chat model override, default `gemini-2.5-pro` |
| `FLASK_SECRET_KEY` | `frontend` | Yes | Flask session signing key |
| `GOOGLE_CLIENT_ID` | `frontend` | Yes for Google login | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | `frontend` | Yes for Google login | Google OAuth client secret |
| `FRONTEND_PUBLIC_URL` | `frontend` | Yes | Public frontend base URL used for OAuth redirects |
| `API_PORT` / `API_INTERNAL_PORT` | `apis` | No | Host/internal API ports, default `8000` |
| `FRONTEND_PORT` / `FRONTEND_INTERNAL_PORT` | `frontend` | No | Host/internal frontend ports, default `3000` |
| `PYTHON_IMAGE_TAG` | Docker builds | No | Python base image version, default `3.14` |
| `SCRAPER_TERMS` | `scrapers` | No | Comma-separated term codes or `auto` |
| `SCRAPE_INTERVAL_HOURS` | `scrapers` | No | Hours between scraper cycles, default `24` |

Generate local secrets with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

For Google OAuth local development, add this redirect URI in Google Cloud Console:

```text
http://localhost:3000/auth/google/callback
```

For the deployed app, add:

```text
https://squid-app-3b9ec.ondigitalocean.app/auth/google/callback
```

## Run Locally

Start the full stack with Docker Compose:

```bash
cp .env.example .env
# Edit .env and fill in Gemini, OAuth, Flask, and internal API secrets.
docker compose up --build
```

Services:

- Frontend: http://localhost:3000
- API health check: http://localhost:8000/health
- MongoDB host access: `127.0.0.1:${MONGO_PORT:-27017}`

Stop the stack with:

```bash
docker compose down
```

The MongoDB data volume is named `mongo_data`, so local data survives container rebuilds unless you remove the volume.

## Data Setup

The scraper service can populate MongoDB with NYU course and program data. With the Compose stack running, the `scrapers` service runs `run_daily_scrape.py` and repeats on the interval configured by `SCRAPE_INTERVAL_HOURS`.

To run a one-off Bulletin scrape manually:

```bash
docker compose run --rm scrapers python scraper.py --term 1268 --subject CSCI-UA --details --to-mongo "mongodb://mongo:27017/final_project"
```

To list available Bulletin schools:

```bash
docker compose run --rm scrapers python scraper.py
```

Albert section data requires a logged-in browser session. Start a Chromium-based browser with remote debugging enabled:

```bash
"<browser-exe>" --remote-debugging-port=9222 --user-data-dir="/tmp/albert-cdp-profile"
```

Log in to Albert in that browser, pass reCAPTCHA, and open the Browse by Subject page. Then run:

```bash
python scrapers/albert_scraper.py --cdp-url http://127.0.0.1:9222
```

The Albert scraper writes `scrapers/classes_example.json` and `scrapers/classes_example_report.json` for review. Use `scrapers/load_mongo.py` when you need to import a local Albert JSON export into MongoDB.

## Run Individual Images

API service:

```bash
docker run --rm -p 8000:8000 \
  -e MONGO_URI="mongodb://host.docker.internal:27017/final_project" \
  -e MONGO_DB_NAME=final_project \
  -e API_INTERNAL_TOKEN="shared-token" \
  -e GEMINI_API_KEY="your-key" \
  kylec55/api-service:latest
```

Frontend:

```bash
docker run --rm -p 3000:3000 \
  -e API_URL=http://host.docker.internal:8000 \
  -e API_INTERNAL_TOKEN="shared-token" \
  -e FLASK_SECRET_KEY="your-secret" \
  -e FRONTEND_PUBLIC_URL=http://localhost:3000 \
  kylec55/web-app:latest
```

Scraper:

```bash
docker run --rm \
  kylec55/scraper:latest \
  python scraper.py --term 1268 --subject CSCI-UA --details \
    --to-mongo "mongodb://host.docker.internal:27017/final_project"
```

## API Endpoints

Common backend endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | API health check |
| `GET` | `/classes` | Paginated course and section search |
| `POST` | `/classes/reload` | Refresh a course from Bulletin data |
| `GET` | `/classes/schools` | School filter values |
| `GET` | `/professors` | Professor search |
| `GET` | `/professors/profile` | Professor profile and course data |
| `POST` | `/auth/register` | NYU email registration |
| `POST` | `/auth/login` | Email/password login |
| `POST` | `/auth/google` | Google OAuth user upsert |
| `GET` / `PUT` | `/user/profile` | Student profile read/update |
| `POST` | `/user/transcript` | Transcript PDF upload and parsing |
| `GET` | `/programs` | Undergraduate program list |
| `GET` | `/program-requirements` | Requirement tables for a program URL |
| `POST` | `/chat` | Gemini-powered AI course assistant |

The frontend exposes protected `/api/*` proxy routes for browser calls and injects `X-Internal-API-Token` for protected backend endpoints.

## Testing

Run tests from the repository root:

```bash
pytest tests/
pytest apis/tests/
pytest frontend/tests/
```

The GitHub Actions workflows also run subsystem tests with coverage before building and publishing Docker images.

## CI/CD

Each custom subsystem has its own GitHub Actions workflow:

| Workflow | Watches | Publishes |
|---|---|---|
| `.github/workflows/api-service.yml` | `apis/**` | `DOCKER_USERNAME/api-service:latest` |
| `.github/workflows/web-app.yml` | `frontend/**` | `DOCKER_USERNAME/web-app:latest` |
| `.github/workflows/scraper.yml` | `scrapers/**` | `DOCKER_USERNAME/scraper:latest` |

Required GitHub Actions secrets:

| Secret | Description |
|---|---|
| `DOCKER_USERNAME` | Docker Hub username |
| `DOCKER_PASSWORD` | Docker Hub password or access token |
| `GEMINI_API_KEY` | Google Gemini API key used by the API service |

Workflows run on pushes and pull requests to `main` and `master`. Docker images are pushed only on direct pushes to `main` or `master`.

## DigitalOcean Deployment

Production runs with Docker Compose on DigitalOcean. Compose starts `frontend`, `apis`, `scrapers`, and `mongo`, and stores MongoDB data in the persistent `mongo_data` volume.

Production `.env` should use the internal Compose MongoDB URI:

```bash
MONGO_URI=mongodb://mongo:27017/final_project
MONGO_DB_NAME=final_project
MONGO_PORT=27017
FRONTEND_PUBLIC_URL=https://squid-app-3b9ec.ondigitalocean.app
```

After deployment, verify:

- The app loads at https://squid-app-3b9ec.ondigitalocean.app/?term=1268&page=1.
- Google login redirects to `/auth/google/callback` successfully.
- The frontend can reach the backend API.
- `GET /health` returns a healthy response.
- Course search returns results.
- The scraper writes course and program data into MongoDB.
- MongoDB data persists after containers are rebuilt or restarted.

## Development Notes

- `frontend/app/main.py` is the frontend entrypoint and proxy layer.
- `frontend/app/templates/` contains the Search, Schedule, Programs, Profile, Graduation, Professor, Login, and shared Chat templates.
- `apis/app/main.py` is the API entrypoint and registers the chat blueprint.
- `apis/app/ai/` contains the Gemini client, tool-calling loop, and MongoDB-backed AI tools.
- `apis/app/services/transcript_parser.py` parses uploaded transcript PDFs with regex-first logic and an AI fallback.
- `apis/app/services/professor_ratings.py` performs Rate My Professors lookups and MongoDB-backed caching.
- `scrapers/scraper.py` is the main Bulletin scraper CLI.
- `scrapers/albert_scraper.py` handles Albert scraping through an already authenticated browser session.

## Known Constraints

- Albert scraping requires manual login and cannot be fully automated.
- Program requirement parsing depends on NYU Bulletin page structure.
- Professor ratings depend on external Rate My Professors pages and name matching.
- The AI assistant requires a valid Gemini API key.
