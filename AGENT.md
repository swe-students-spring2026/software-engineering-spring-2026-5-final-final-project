# AGENT.md

## 1. Project Overview

**Project Name:** AI Course Selection Assistant
**Type:** Full-stack web application with AI-powered course planning
**Target University:** NYU (New York University)
**Deployment Target:** Docker Compose locally; migration to Digital Ocean (cloud-hosted) planned

This application helps NYU students plan their semester by combining course catalog data, section-level scheduling, graduation requirements, professor ratings, and the student's academic history. A Gemini-powered AI agent interprets natural language requests, queries the database, and generates grounded course recommendations.

---

## 2. System Architecture

Three Docker services defined in `docker-compose.yml`:

| Service | Container | Port (default) | Description |
|---------|-----------|----------------|-------------|
| `apis` | `backend` | 8000 | Flask REST API — AI, tools, data queries |
| `frontend` | `frontend` | 3000 | Flask server-side frontend — proxies to API |
| `scrapers` | `crawlers` | — | Long-running scraper worker — runs daily |

### 2.1 Flask API (`apis/`)

Entry point: `apis/app/main.py`

**Routes (`apis/app/routes/`)**
- `chat.py` — `/api/chat` POST — stateless AI chat endpoint; accepts transcript + conversation history, returns AI response

**Services (`apis/app/services/`)**
- `professor_ratings.py` — fetches professor ratings from Rate My Professors via BeautifulSoup scraping; results cached in MongoDB with a TTL index; parallel lookups via `ThreadPoolExecutor`
- `requirements_service.py` — reads program requirement documents from the `program_requirements` collection
- `transcript_parser.py` — parses uploaded transcript text into a structured list of completed courses; uses regex-first approach with Gemini AI fallback

**AI layer (`apis/app/ai/`)**
- `client.py` — initializes the `google-genai` Gemini client; guards against missing API key
- `service.py` — runs the Gemini tool-calling loop; sends messages, executes tool calls, accumulates results
- `tools.py` — defines MongoDB-backed tools callable by the AI:
  - `search_courses` — `$text` index search across name, description, subject
  - `get_course_sections` — section-level details including meeting times and enrollment status
  - `get_professor_rating` — delegates to `professor_ratings.py`
  - `get_program_requirements` — returns scraped bulletin requirement text
  - `get_completed_courses` — reads a user's transcript from the `users` collection

**Other endpoints in `main.py`**
- `GET /api/courses` — paginated course list with optional school/component filters
- `GET /api/courses/<id>/sections` — sections for a single course
- `GET /api/programs` — program requirements list (cached 5 min)
- `POST /api/transcript` — stores parsed transcript to user record
- Startup hook: creates MongoDB indexes on `classes` and `bulletin_classes`

### 2.2 Flask Frontend (`frontend/`)

Entry point: `frontend/app/main.py`

- Server-side rendered UI (Jinja2 templates)
- Google OAuth 2.0 login (`GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`)
- Session management via `FLASK_SECRET_KEY`
- Proxies all `/api/*` calls to the API container with per-call timeouts (`_T_SHORT=5s`, `_T_NORMAL=30s`, `_T_LONG=120s`)
- Propagates `Cache-Control` headers from API responses

### 2.3 Scraper Worker (`scrapers/`)

Orchestrated by `run_daily_scrape.py` which loops on a configurable interval (`SCRAPE_INTERVAL_HOURS`, default 24).

Each subsystem runs in an isolated `try/except` block — one failure does not abort the others.

| File | What it scrapes | Source |
|------|----------------|--------|
| `bulletins.py` + `scraper.py` | Course catalog + section data | `bulletins.nyu.edu` public API |
| `albert_scraper.py` | Section enrollment + meeting detail | NYU Albert SIS (Playwright, login required) |
| `load_mongo.py` | One-shot bulk loader for Albert JSON exports | Local JSON files |

**Albert scraper note:** Albert requires a logged-in browser session. The scraper uses Playwright and must be triggered manually by a user who hooks it into an authenticated browser. It cannot run in the automated daily cycle.

---

## 3. Database

**Provider:** MongoDB Atlas
**Config env vars:** `MONGO_URI`, `MONGO_DB_NAME`

| Collection | Contents | Primary index |
|-----------|----------|---------------|
| `bulletin_classes` | Course + section records from bulletins API | `course_code`, text index on name/description |
| `program_requirements` | Scraped degree requirement pages from bulletins.nyu.edu | `url` (unique), text index on title/requirements/description |
| `users` | User records including stored transcript / taken courses | `google_id` |
| `professor_ratings_cache` | Cached RMP professor rating lookups | `professor_name` + `school` (TTL) |
| `classes` | Albert-scraped section records | `class_number`, `course_code` |

---

## 4. AI Configuration

**Model:** `GEMINI_MODEL` env var (default: `gemini-2.0-flash`)
**SDK:** `google-genai`

The AI runs a synchronous tool-calling loop: it receives a system prompt + conversation history, calls tools (defined in `tools.py`) as needed, and returns a final natural-language response. Tools are MongoDB-backed; no hallucinated data is returned.

---

## 5. Data Sources

| Source | Access Method | Automated |
|--------|---------------|-----------|
| NYU Bulletins course catalog | HTTP + BeautifulSoup (`bulletins.py`, `scraper.py`) | Yes — daily |
| NYU Bulletins program requirements | HTTP + BeautifulSoup (`bulletins.py`) | Yes — daily |
| NYU Albert (sections + enrollment) | Playwright browser automation (`albert_scraper.py`) | No — manual login required |
| Rate My Professors | HTTP + BeautifulSoup (`professor_ratings.py`) | On-demand (per request) |

---

## 6. Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGO_URI` | Yes | MongoDB Atlas connection string |
| `MONGO_DB_NAME` | Yes | Database name |
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `GEMINI_MODEL` | No | Model name (default: `gemini-2.0-flash`) |
| `FLASK_SECRET_KEY` | Yes | Flask session signing key |
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Yes | Google OAuth client secret |
| `FRONTEND_PUBLIC_URL` | Yes | Public base URL for OAuth redirect |
| `API_PORT` | No | Host port for API (default: 8000) |
| `FRONTEND_PORT` | No | Host port for frontend (default: 3000) |
| `SCRAPER_TERMS` | No | Comma-separated term codes or `auto` (default: `auto`) |
| `SCRAPE_INTERVAL_HOURS` | No | Hours between scrape cycles (default: 24) |

---

## 7. Running Locally

```bash
# Copy and fill in environment values
cp .env.example .env

# Build and start all three services
docker compose up --build

# Frontend:  http://localhost:3000
# API:       http://localhost:8000
```

To run the Albert scraper manually:
```bash
cd scrapers
playwright install chromium
python albert_scraper.py   # follow prompts to log in via browser
```

---

## 8. Testing

Tests live in `apis/tests/` and `frontend/tests/`.

```bash
# From repo root
pytest apis/tests/
pytest frontend/tests/
```

Key test files:
- `test_professor_ratings.py` — mocks `_rmp_get` wrapper, covers cache hit/miss and no-mutation of inputs
- `test_tools.py` — verifies AI tool handlers return correct shapes
- `test_transcript_parser.py` — covers regex path and AI fallback path
- `test_requirements_service.py` — verifies program requirement queries

---

## 9. Planned Migration

The application is currently run via Docker Compose on a local or self-hosted machine. The planned next step is to migrate to **Digital Ocean** as a fully cloud-hosted deployment. This will involve:

- Hosting all services on a Digital Ocean Droplet via Docker Compose
- **Replacing MongoDB Atlas with a local MongoDB container** running on the same Droplet — `MONGO_URI` will point to the containerized instance instead of Atlas
- Adding a `mongo` service to `docker-compose.yml` with a named volume for data persistence
- Pointing `FRONTEND_PUBLIC_URL` and OAuth redirect URIs to the public domain
- Managing secrets via Digital Ocean environment config or a secrets manager
- Ensuring the scraper worker's persistent loop (`run_daily_scrape.py`) runs as a long-lived background process

---

## 10. Known Constraints

- Albert scraping requires manual user login — cannot be fully automated
- Program requirements coverage depends on NYU Bulletins page structure remaining stable
- Gemini tool-calling is synchronous; very long conversations may hit response time limits
- Not all NYU majors/schools have complete program requirement pages scraped
- RMP professor lookups depend on name matching — uncommon name spellings may miss results
