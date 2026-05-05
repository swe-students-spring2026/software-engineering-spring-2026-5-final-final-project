# MongoDB Subsystem

This subsystem provides MongoDB Atlas integration for caching search results in the Rove Beetle Crew NYC Safe Place Finder app.

## What it does

- Caches ML pipeline search results so repeated queries return instantly
- Stores each result keyed by a SHA-256 hash of the user's query
- Gracefully skips caching if MongoDB is unreachable, so the app still works

## Setup

### 1. Create a MongoDB Atlas account

- Go to [https://www.mongodb.com/atlas](https://www.mongodb.com/atlas)
- Create a free account and a free **M0** cluster
- Under **Database Access**, create a new user with read/write permissions
- Under **Network Access**, add `0.0.0.0/0` to allow connections from anywhere

### 2. Get your connection string

- In Atlas, click **Connect** on your cluster
- Choose **Drivers** → **Python**
- Add the database name `rove_beetle` 

### 3. Set up your `.env` file

```bash
cp env.example .env
```

Then fill in your connection string in `.env`.

**Never commit your `.env` file to GitHub.** It is already listed in `.gitignore`.

## Usage

The `api.py` service exposes these endpoints:

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Ping MongoDB Atlas |
| `/cache` | GET | Get cached result by query |
| `/cache` | POST | Save a result to cache |
| `/cache` | DELETE | Clear all cached results |

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `MONGO_URI` | Yes | MongoDB Atlas connection string |

## Database Structure

- **Database:** `rove_beetle`
- **Collection:** `search_cache`
- **Document format:**
```json
  {
    "_id": "<sha256 hash of query>",
    "query": "a quiet place to study where it's also safe",
    "data": {
      "place_type": "...",
      "reversed_attribute": "...",
      "results": [...]
    },
    "cached_at": "2026-05-05T12:00:00+00:00"
  }
```