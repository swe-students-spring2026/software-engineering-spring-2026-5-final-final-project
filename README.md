# CineMatch

[![Event Logger](https://github.com/swe-students-spring2026/5-final-lime_llama-2/actions/workflows/event-logger.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-lime_llama-2/actions/workflows/event-logger.yml)
[![Frontend CI/CD](https://github.com/swe-students-spring2026/5-final-lime_llama-2/actions/workflows/frontend.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-lime_llama-2/actions/workflows/frontend.yml)
[![Recommendation Engine CI/CD](https://github.com/swe-students-spring2026/5-final-lime_llama-2/actions/workflows/recommendation-engine.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-lime_llama-2/actions/workflows/recommendation-engine.yml)
[![Nginx CI/CD](https://github.com/swe-students-spring2026/5-final-lime_llama-2/actions/workflows/nginx.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-lime_llama-2/actions/workflows/nginx.yml)

CineMatch is a containerized movie recommendation web application. Users can search for movies, enter four favorite movies to receive personalized recommendations, save movies to a watchlist, and review recommendation/search activity through history and analytics pages.

The recommendation engine uses cosine similarity over precomputed movie embeddings stored in a FAISS index. User accounts, watchlists, and activity history are stored in MongoDB.

## Team

- [Laura Liu](https://github.com/lauraliu518)
- [Ethan Demol](https://github.com/ethandemol)
- [Yutong Liu](https://github.com/Abbyyyt)
- [Owen Zhang](https://github.com/owenzhang2004)
- [Howard Xia](https://github.com/hewlett-packard-lovecraft)

## Features

- Search movies by title, overview text, or genre.
- Use natural-language queries such as "slow-burn psychological thriller".
- Enter four favorite movies and receive cosine-similarity recommendations.
- View movie detail pages with title, description, genre, year, rating, director, cast, and similar movies.
- Register, log in, and maintain a personal watchlist.
- Store recommendation and search history in MongoDB.
- View a simple analytics dashboard for search, recommendation, semantic-search, and watchlist activity.
- Run the application locally or through Docker Compose.

## Repository Structure

```text
.
|-- frontend/                  # Flask web app, routes, templates, static assets
|-- recommendation-engine/     # Flask API, FAISS loading, recommendation logic
|-- recommendation-engine/data # Generated FAISS index and metadata files, gitignored
|-- nginx/                     # Reverse proxy used by Docker Compose
|-- tests/                     # Existing frontend and recommendation-engine tests
|-- .github/workflows/         # Event logger and subsystem CI/CD workflows
|-- docker-compose.yml         # Multi-service container configuration
|-- .env.example               # Dummy environment variable template
|-- pyproject.toml             # Pytest configuration
`-- README.md
```

## Architecture

The system is organized into four subsystems:

1. **MongoDB**  
   Stores users, password hashes, watchlist entries, and search/recommendation history. The application can use MongoDB Atlas or a local MongoDB instance through `MONGO_URI`.

2. **frontend**  
   A Flask web app in `frontend/`. It renders the UI, handles authentication, reads/writes MongoDB data, and calls the recommendation engine through HTTP.

3. **recommendation-engine**  
   A Flask API in `recommendation-engine/`. It loads `faiss.index` and `metadata.parquet`, searches movie metadata, maps favorite titles to movie IDs, and returns ranked recommendations.

4. **nginx**  
   A reverse proxy in `nginx/`. Requests to `/api/*` are forwarded to the recommendation engine; all other requests are forwarded to the frontend.

## Docker Images

Each custom subsystem has a Dockerfile:

- `frontend/Dockerfile`
- `recommendation-engine/Dockerfile`
- `nginx/Dockerfile`

TODO: Publish these images to Docker Hub and replace the placeholders below:

- Frontend: `https://hub.docker.com/r/<dockerhub-user-or-org>/cinematch-frontend`
- Recommendation engine: `https://hub.docker.com/r/<dockerhub-user-or-org>/cinematch-recommendation-engine`
- Nginx: `https://hub.docker.com/r/<dockerhub-user-or-org>/cinematch-nginx`

## Environment Variables

Do not commit real secrets. The repository includes `.env.example` with dummy values only. Real MongoDB Atlas credentials and secret keys should be shared through a private course-approved channel.

For local Flask development, create `frontend/.env`:

```env
MONGO_URI=mongodb+srv://username:password@cluster0.example.mongodb.net/cinematch
SECRET_KEY=change-me-to-a-long-random-string
REC_API_URL=http://localhost:5001
INDEX_PATH=recommendation-engine/data/faiss.index
METADATA_PATH=recommendation-engine/data/metadata.parquet
```

For Docker Compose, create a repository-root `.env` because `docker-compose.yml` uses `env_file: .env`.

The important variables are:

- `MONGO_URI`: MongoDB Atlas or local MongoDB connection string.
- `SECRET_KEY`: Flask session signing key.
- `REC_API_URL`: Base URL for the frontend to call the recommendation engine.
- `INDEX_PATH`: Path to the FAISS index.
- `METADATA_PATH`: Path to the movie metadata parquet file.
- `RECOMMENDATION_PORT`: Port for the recommendation-engine Flask app, default `5001`.

## Data Preparation

The recommendation engine does not start successfully until these generated files exist:

```text
recommendation-engine/data/faiss.index
recommendation-engine/data/metadata.parquet
```

Generate them from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r recommendation-engine\requirements.txt
.\.venv\Scripts\python.exe recommendation-engine\scripts\preprocess.py
```

The preprocessing script downloads `Remsky/Embeddings__Ultimate_1Million_Movies_Dataset` from Hugging Face, parses the embedding column, builds a FAISS `IndexFlatIP`, and writes the generated files into `recommendation-engine/data/`. These files are intentionally gitignored because they are large.

## MongoDB Setup

After configuring `MONGO_URI`, create the MongoDB indexes used by the frontend:

```powershell
cd D:\2026_Spring\SWE\5-final-lime_llama-2\frontend
..\.venv\Scripts\python.exe setup_db.py
```

The setup script creates indexes for:

- unique user email addresses
- unique usernames
- one watchlist entry per user and movie
- history lookup by user and timestamp

## Local Setup on Windows

From the repository root:

```powershell
cd D:\2026_Spring\SWE\5-final-lime_llama-2
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r frontend\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r recommendation-engine\requirements.txt
Copy-Item .env.example frontend\.env
Copy-Item .env.example .env
```

Edit both `.env` files with real local credentials, but do not commit them.

Start the recommendation engine in one terminal:

```powershell
cd D:\2026_Spring\SWE\5-final-lime_llama-2\recommendation-engine
$env:INDEX_PATH="data/faiss.index"
$env:METADATA_PATH="data/metadata.parquet"
$env:RECOMMENDATION_PORT="5001"
..\.venv\Scripts\python.exe app.py
```

Start the frontend in a second terminal:

```powershell
cd D:\2026_Spring\SWE\5-final-lime_llama-2\frontend
$env:REC_API_URL="http://localhost:5001"
..\.venv\Scripts\python.exe app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Local Setup on macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r frontend/requirements.txt
python -m pip install -r recommendation-engine/requirements.txt
cp .env.example frontend/.env
cp .env.example .env
```

Edit both `.env` files with real local credentials, generate the FAISS data, and then run:

```bash
cd recommendation-engine
INDEX_PATH=data/faiss.index METADATA_PATH=data/metadata.parquet RECOMMENDATION_PORT=5001 ../.venv/bin/python app.py
```

In another terminal:

```bash
cd frontend
REC_API_URL=http://localhost:5001 ../.venv/bin/python app.py
```

Open `http://127.0.0.1:5000`.

## Run with Docker Compose

After the repository-root `.env` is configured and the FAISS data files exist:

```powershell
docker compose up --build
```

This starts:

- `recommendation-engine`
- `frontend`
- `nginx`

Open:

```text
http://localhost
```

Stop the system:

```powershell
docker compose down
```

## Testing

The project already includes tests under `tests/frontend/` and `tests/recommendation_engine/`.

Install dependencies and run the suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r frontend\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r recommendation-engine\requirements.txt
.\.venv\Scripts\python.exe -m pip install pytest pytest-cov
.\.venv\Scripts\python.exe -m pytest
```

## CI/CD

The repository includes the instructor-provided event logging workflow:

- `.github/workflows/event-logger.yml`

It also includes separate subsystem workflows for:

- `.github/workflows/frontend.yml`
- `.github/workflows/recommendation-engine.yml`
- `.github/workflows/nginx.yml`

These workflows run the existing unit tests, validate or build the service Docker images, push images to Docker Hub, and deploy services to Digital Ocean.

## Technologies Used

- Python
- Flask
- Jinja
- MongoDB Atlas or local MongoDB
- PyMongo and Flask-PyMongo
- bcrypt
- FAISS
- pandas
- Hugging Face datasets
- Docker
- Docker Compose
- Nginx
- GitHub Actions
