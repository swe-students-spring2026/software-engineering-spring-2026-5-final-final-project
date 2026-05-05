# Final Project

An exercise to put to practice software development teamwork, subsystem communication, containers, deployment, and CI/CD pipelines. See [instructions](./instructions.md) for details.

## Frontend Features

1. Users can enter four favorite movies to receive personalized movie recommendations.
2. The application generates recommendation results based on cosine similarity.
3. Users can search directly by movie title.
4. Users can make natural-language semantic searches, such as describing the type of movie they want to watch.
5. Each movie has a detail page with key information such as title, description, genre, year, rating, director, and cast.
6. Movie detail pages can display similar movie recommendations.
7. Users can save movies to a personal watchlist.
8. Recommendation history is stored in MongoDB for later retrieval.
9. A simple analytics dashboard summarizes recommendation and search activity.

## Description

CineMatch is a movie recommendation web app that learns your taste from just four films. Tell us your four all-time favourite movies and we'll offer a personalised list of films you're likely to love — powered by cosine similarity over pre-computed semantic embeddings from a dataset of one million movies.

You can also search the catalogue in two ways: type a title like "Gladiator" for a direct lookup, or describe what you're in the mood for — "a slow-burn psychological thriller like Christopher Nolan" — and the semantic search engine will find the closest matches based on meaning, not just keywords.


## Setup

> **System requirements:** 16GB+ RAM, ~10GB free disk. Python 3.12 recommended.

### 1. Create venv and install deps (~5 min)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r frontend/requirements.txt
pip install -r recommendation-engine/requirements.txt
```

### 2. Build the FAISS index (~15-60 min)
This downloads a 7GB embedded movie dataset from HuggingFace, parses 1M+ embeddings into memory, builds a FAISS index, and writes `data/faiss.index` (3GB) + `data/metadata.parquet` (288MB).

```bash
cd recommendation-engine
python scripts/preprocess.py
cd ..
```

> **macOS users:** Close Chrome and other memory-heavy apps before running this. Peak memory usage is ~12GB. Disable Low Power Mode.
### 3. Configure environment
Copy the example file and fill in your values:

```bash
cp .env.example frontend/.env
```

Edit `frontend/.env`:

MONGO_URI=mongodb+srv://...     # provided separately
SECRET_KEY=any-long-random-string
RECOMMENDATION_API_URL=http://localhost:8000

### 4. macOS-only: install certificates for Mongo TLS

If you installed Python from python.org (not Homebrew or pyenv), run:

```bash
/Applications/Python\ 3.12/Install\ Certificates.command
```

Without this, the frontend will fail to connect to MongoDB Atlas with `CERTIFICATE_VERIFY_FAILED`.

### 5. Run the services

In **terminal 1**, start the recommendation engine (port 8000):
```bash
cd recommendation-engine
source ../.venv/bin/activate
python app.py
```

Wait for `Service ready.` (first run downloads ~550MB of model weights).

In **terminal 2**, start the frontend (port 5000):
```bash
cd frontend
source ../.venv/bin/activate
python app.py
```

Open `http://localhost:5000` in your browser.

### 6. Smoke test (optional)

```bash
curl localhost:8000/health
# {"movies": 1035695, "status": "ok"}
```