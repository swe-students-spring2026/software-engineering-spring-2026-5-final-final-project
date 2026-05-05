# ML Service — Mood Music Recommender

Weather + mood → Spotify playlist, powered by Claude API.  
Runs as a single Docker container with a local MongoDB sidecar.

---

## Stack

| Layer | Tech |
|---|---|
| API framework | FastAPI + Uvicorn |
| NLP / mood parsing | Anthropic Claude API |
| Music recommendations | Spotify Web API (spotipy) |
| Weather | OpenWeatherMap API |
| Database | MongoDB (Mongoose-compatible) |
| Container | Docker + docker-compose |

---

## Project structure

```
ml-service/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── app/
    ├── main.py          # FastAPI routes
    ├── mood_parser.py   # Claude API → audio profile
    ├── recommender.py   # Spotify API → track list
    ├── weather.py       # OpenWeatherMap proxy
    ├── database.py      # MongoDB helpers
    ├── schemas.py       # Pydantic models
    └── config.py        # Settings from env vars
```

---

## Quick start

### 1. Copy and fill in your keys

```bash
cp .env.example .env
# Edit .env with your API keys
```

You need:
- `ANTHROPIC_API_KEY` — from https://console.anthropic.com
- `SPOTIFY_CLIENT_ID` + `SPOTIFY_CLIENT_SECRET` — from https://developer.spotify.com/dashboard
- `OPENWEATHER_API_KEY` — from https://openweathermap.org/api (free tier works)

### 2. Run with Docker

```bash
docker-compose up --build
```

Service starts at **http://localhost:8000**  
Interactive API docs at **http://localhost:8000/docs**

### 3. Run locally (without Docker)

```bash
pip install -r requirements.txt
cd app
uvicorn main:app --reload --port 8000
```

---

## API reference

### `GET /health`
Simple health check.

---

### `GET /weather?lat=40.71&lon=-74.01`
Fetches current weather for a coordinate pair (from browser geolocation).

**Response:**
```json
{
  "temp": 8.2,
  "condition": "light drizzle",
  "humidity": 81,
  "city": "New York",
  "icon": "09d"
}
```

### `GET /weather/city?city=London`
Fallback — fetch weather by city name.

---

### `POST /predict`
Core endpoint. Accepts mood + weather, returns ranked track list.

**Request:**
```json
{
  "mood": "cozy and a bit sad",
  "weather": {
    "temp": 8.2,
    "condition": "light drizzle",
    "humidity": 81,
    "city": "New York"
  },
  "user_id": "spotify:user:abc123",
  "limit": 20
}
```

**Response:**
```json
{
  "tracks": [
    {
      "uri": "spotify:track:...",
      "name": "Holocene",
      "artist": "Bon Iver",
      "album": "Bon Iver, Bon Iver",
      "preview_url": "https://...",
      "external_url": "https://open.spotify.com/track/...",
      "valence": 0.22,
      "energy": 0.31
    }
  ],
  "profile": {
    "valence": 0.28,
    "energy": 0.35,
    "danceability": 0.40,
    "tempo_min": 60,
    "tempo_max": 90,
    "genres": ["sad-indie", "folk"],
    "reasoning": "Cozy + drizzle suggests slow, warm, introspective music."
  },
  "session_id": "664abc123def456"
}
```

---

### `POST /feedback`
User rates a track to improve future recommendations.

**Request:**
```json
{
  "session_id": "664abc123def456",
  "track_uri": "spotify:track:...",
  "rating": 4
}
```

---

## How the mood + weather fusion works

```
User types mood  ──┐
                   ├──► Claude API ──► audio profile (valence, energy, tempo, genres)
Weather (auto)  ──┘                        │
                                           ▼
                               Spotify recommendations API
                                           │
                                           ▼
                                   Ranked track list
```

Claude is prompted to treat mood as the **primary** signal and weather as a
**secondary modifier** — so a user who says "energetic" on a rainy day still
gets upbeat music, just perhaps with a slightly grittier edge.

---

## Connecting to the web app

The web app (Node/Express) calls this service at `http://ml-service:8000`
when running inside the same Docker network. Add to the web app's
`docker-compose.yml`:

```yaml
networks:
  default:
    external:
      name: ml-service_default
```

Or merge both compose files and reference `ml-service` as the hostname directly.

---

## MongoDB collections

| Collection | Contents |
|---|---|
| `sessions` | Every prediction request — mood, weather, profile, tracks |
| `feedback` | User ratings (1–5) per track per session |
| `playlists` | (Populated by web app) Created Spotify playlist IDs |
