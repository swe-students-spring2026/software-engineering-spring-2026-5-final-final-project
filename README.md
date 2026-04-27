# Music Recommendation API

A small FastAPI backend for a school-project music recommendation system. The service stores users, songs, and listening feedback in SQLite, then uses item-based collaborative filtering to recommend songs and find similar tracks.

## Proposed File Tree

```text
.
├── README.md
├── requirements.txt
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── recommender.py
│   └── seed.py
└── tests/
    └── test_api.py
```

## What The Project Does

The API lets teammates create users and songs, record feedback events such as plays, likes, skips, and saves, train a collaborative-filtering model, and request recommendations.

The backend has two response modes:

- `mock`: returned before a model has been trained, using realistic sample song data so frontend and integration work can continue.
- `model`: returned after `POST /train` builds the collaborative-filtering model from stored events.

## API Endpoints

### `GET /health`

Returns server status.

```json
{
  "status": "ok"
}
```

### `POST /users`

Creates a user.

Request:

```json
{
  "user_id": "u1",
  "name": "Avery"
}
```

### `POST /songs`

Creates a song.

Request:

```json
{
  "song_id": "s1",
  "title": "Midnight City",
  "artist": "M83",
  "genre": "Electronic"
}
```

### `POST /events`

Records user feedback.

Supported `event_type` values:

- `play`
- `skip`
- `like`
- `dislike`
- `save`
- `repeat`

Request:

```json
{
  "user_id": "u1",
  "song_id": "s1",
  "event_type": "like"
}
```

### `GET /recommendations/{user_id}?k=10`

Returns recommended songs for a user.

Example mock response:

```json
{
  "user_id": "u1",
  "source": "mock",
  "recommendations": [
    {
      "song_id": "sample-1",
      "title": "Golden Hour Drive",
      "artist": "The Demo Tapes",
      "genre": "Indie Pop",
      "score": 0.94
    }
  ]
}
```

Example model response:

```json
{
  "user_id": "u1",
  "source": "model",
  "recommendations": [
    {
      "song_id": "s4",
      "title": "Dreams",
      "artist": "Fleetwood Mac",
      "genre": "Rock",
      "score": 0.72
    }
  ]
}
```

### `GET /songs/{song_id}/similar?k=10`

Returns songs most similar to the requested song.

### `POST /train`

Rebuilds the collaborative-filtering model from stored events.

## How Collaborative Filtering Works

Collaborative filtering recommends items by learning from user behavior instead of hand-written rules. This project uses item-based collaborative filtering:

1. Convert feedback events into numeric weights.
2. Build a user-song matrix where each row is a user and each column is a song.
3. Use cosine similarity to compare song columns.
4. Recommend unseen songs that are similar to songs the user responded to positively.

Feedback weights:

| Event | Weight |
| --- | ---: |
| play | 1 |
| skip | -1 |
| like | 5 |
| dislike | -5 |
| save | 4 |
| repeat | 3 |

## How Feedback Updates Recommendations

Every event is stored in SQLite. When `POST /train` is called, the model is rebuilt from all stored feedback. New likes, saves, repeats, plays, skips, and dislikes change the user-song matrix, which can change both recommendations and similar-song results.

For example, if a user likes more upbeat electronic songs, future recommendations will favor unseen songs that other users interacted with in similar patterns. If the user skips or dislikes a song, that negative signal reduces the chance of similar songs being recommended.

## Run Locally

Create and activate a virtual environment if desired, then install dependencies:

```bash
pip install -r requirements.txt
```

Seed the SQLite database:

```bash
python -m app.seed
```

Start the API server:

```bash
uvicorn app.main:app --reload
```

Then train and test recommendations:

```bash
curl -X POST http://127.0.0.1:8000/train
curl "http://127.0.0.1:8000/recommendations/u1?k=5"
curl "http://127.0.0.1:8000/songs/s1/similar?k=5"
```

The API docs are available at:

- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/openapi.json

## Mocked Endpoint Testing

Teammates can test before training the model:

1. Start the server.
2. Create or seed users and songs.
3. Call recommendation endpoints without calling `POST /train`.

Responses will include `"source": "mock"` so callers know they are using fallback sample data. After training succeeds, responses include `"source": "model"`.

## Tests

Run:

```bash
pytest
```

Tests use an isolated temporary SQLite database and do not require the seeded local database.
