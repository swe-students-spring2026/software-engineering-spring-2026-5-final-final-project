# NYC 311 Smart Spot Finder

[![ML Service CI/CD](https://github.com/swe-students-spring2026/5-final-rove_beetle_crew/actions/workflows/ml.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-rove_beetle_crew/actions/workflows/ml.yml)
[![Web App CI/CD](https://github.com/swe-students-spring2026/5-final-rove_beetle_crew/actions/workflows/webapp.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-rove_beetle_crew/actions/workflows/webapp.yml)

---

## About

**NYC 311 Smart Spot Finder** is a web application that helps New Yorkers discover the best spots in the city based on what they're looking for. Users can search for places using natural-language prompts like *"find me a safe spot"* or *"suggest a quiet study spot"*  — and the app responds with real, data-backed location recommendations.

Under the hood, the app uses the open-source [NYC 311 Service Requests dataset](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9/about_data) and the [NYC Facilities Database](https://data.cityofnewyork.us/City-Government/Facilities-Database/ji82-xba5/about_data) to understand neighborhood conditions and match them to user intent via a machine learning model.

---

## Architecture

The project is a monorepo composed of **2 containerized subsystems**:

```

                          Monorepo

     web-app/                    ML/
    (Flask frontend)   →   (ML REST API)
     Port 5000              Port 8000

    Docker Hub              Docker Hub
    + Digital Ocean         + Digital Ocean

```

| Subsystem | Description |
|-----------|-------------|
| `web-app/` | User-facing Flask web application. Accepts natural-language prompts and displays recommended spots on a map. Calls the ML service via REST API. |
| `ML/` | Python ML service that processes 311 and Facilities data, scores locations via semantic search and custom clustering, and serves recommendations via a REST API (`POST /recommend`). |

---

## Container Images

| Subsystem | Docker Hub Image |
|-----------|-----------------|
| Web App   | `your-dockerhub-username/spot-finder-webapp:latest` |
| ML Service | `your-dockerhub-username/spot-finder-ml:latest` |

> **TODO:** Replace `your-dockerhub-username` with your actual Docker Hub username in the CI/CD workflows under `.github/workflows/`.

---

## Team - Rove Beetle Crew

| Name | GitHub | Role |
|------|--------|------|
| Zeyue Xu | [@zeyuexu123](https://github.com/zeyuexu123) | Data preprocessing & ML pipeline |
| Tae Kim | [@thk224](https://github.com/thk224) | Deployment (Digital Ocean), Docker, Documentation |
| Rohan Ahmad | [@ra4059](https://github.com/ra4059) | Test cases & CI/CD pipeline |
| Caleb Jawharjian | [@calebjawharjian](https://github.com/calebjawharjian) | Frontend web app |
| Zheqi Zhang | [@zheqi111](https://github.com/zheqi111) | Backend & MongoDB |

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (v24+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2+)
- [Git](https://git-scm.com/)
- Python 3.10+ *(only needed if running services outside Docker)*

---

### 1. Clone the Repository

```bash
git clone https://github.com/swe-students-spring2026/5-final-rove_beetle_crew.git
cd 5-final-rove_beetle_crew
```

---

### 2. Configure Environment Variables

```bash
cp env.example .env
```

Open `.env` and fill in your values. See the [Environment Variables](#environment-variables) section below.

---

### 3. Load the Dataset

You have two options:

#### Option A - Recommended: Use Preprocessed Data

Download the preprocessed datasets from Google Drive and place them in `ML/data/processed/`:

 [Download preprocessed data from Google Drive](https://drive.google.com/drive/folders/1mOc7ghd8UTucCuDFEdWuDbvzaNJLh33n?usp=sharing)

Your directory should look like this when done:

```
ML/
 data/
     processed/
         [preprocessed files here]
         ...
```

#### Option B - Manual: Download Raw Data and Preprocess

1. Download the two raw datasets:
   - [311 Service Requests (2020-Present)](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9/about_data)
   - [NYC Facilities Database](https://data.cityofnewyork.us/City-Government/Facilities-Database/ji82-xba5/about_data)

2. Place the downloaded CSV files in `ML/data/raw/`.

3. Run the preprocessing script:

```bash
pip install -r ML/requirements.txt
python ML/src/preprocess.py
```

Output files will be written to `ML/data/processed/`.

---

### 4. Run the Application

```bash
docker compose up --build
```

| Service    | URL                       |
|------------|---------------------------|
| Web App    | http://localhost:5000     |
| ML API     | http://localhost:8000     |

To stop all services:

```bash
docker compose down
```

---

### 5. Test the ML Service Locally (Without Docker)

You can test the ML recommendation engine directly by editing the query in `ML/src/main.py`:

```python
# ML/src/main.py — modify this to test different prompts
query = "a quiet place to study where it's also safe"
```

Then run:

```bash
pip install -r ML/requirements.txt
cd ML/src
python main.py
```

---

## Environment Variables

Copy `env.example` to `.env` and fill in the values below before starting the app.

| Variable | Description | Example |
|----------|-------------|---------|
| `ML_API_URL` | Internal URL of the ML service (used by web-app) | `http://ml:8000` |
| `SECRET_KEY` | Flask secret key — make this a long random string | `change-me-to-something-random` |
| `FLASK_ENV` | Flask environment mode | `development` or `production` |

> **Never commit your `.env` file.** It is listed in `.gitignore`. The file `env.example` in the repo root serves as the canonical template with dummy values.

---

## Repository Structure

```
.
 web-app/                    # Flask frontend
    app.py
    templates/
    static/
    Dockerfile
    requirements.txt

 ML/                         # ML REST API + recommendation engine
    src/
        api.py              # Flask REST API entry point
        main.py             # Entry point for local testing
        preprocess.py       # Data preprocessing script
        clustering.py       # Custom k-means clustering over 311 data
        embedding.py        # Sentence-transformer embeddings
        filter.py           # Core search and filtering logic
        search.py
        split.py
        config.py
    data/
       raw/                # Raw downloaded CSVs (not committed)
       processed/          # Preprocessed data (see setup above)
    Dockerfile
    requirements.txt

 tests/                      # Test suite
    test_basic.py
    test_preprocess.py

 .github/
    workflows/
        webapp.yml          # CI/CD pipeline for web-app
        ml.yml              # CI/CD pipeline for ML service
        test.yml            # General test runner

 docker-compose.yml
 env.example                 # Template — copy to .env and fill in values
 pyproject.toml              # Pytest configuration
 README.md
```

---

## Running Tests

```bash
pip install pytest pandas pytest-cov
pytest
```

The `pyproject.toml` configures pytest to discover tests under the `tests/` directory.

---

## CI/CD Pipelines

Each subsystem has its own GitHub Actions workflow under `.github/workflows/`, triggered on pushes or pull requests to `main` that touch the relevant directory.

| Subsystem  | Workflow File  | Trigger                              |
|------------|----------------|--------------------------------------|
| Web App    | `webapp.yml`   | Push or PR to `main` (web-app files) |
| ML Service | `ml.yml`       | Push or PR to `main` (ML files)      |

Each workflow:
1. Runs the test suite with `pytest` *(on every push and pull request to `main`)*
2. Builds the Docker image *(on push to `main` only, after tests pass)*
3. Pushes the image to Docker Hub *(on push to `main` only)*
4. Deploys to Digital Ocean App Platform *(on push to `main` only, after image is pushed)*

### Required GitHub Repository Secrets

Add these under **Settings → Secrets and variables → Actions** in your GitHub repo:

| Secret | Description |
|--------|-------------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub access token (not your password) |
| `DIGITAL_OCEAN_ACCESS_TOKEN` | Digital Ocean API token |
| `DIGITAL_OCEAN_WEBAPP_ID` | Digital Ocean App Platform app ID for the web-app |
| `DIGITAL_OCEAN_ML_ID` | Digital Ocean App Platform app ID for the ML service |

---

## Live Deployment

The application is deployed to **Digital Ocean** automatically on every push to `main`.

- **Web App**: *(update once deployed)*
- **ML Service**: *(update once deployed)*

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Flask, Jinja2, HTML/CSS/JS |
| ML Engine | Python, sentence-transformers, NumPy, pandas |
| Data Sources | NYC Open Data — 311 Service Requests & Facilities Database |
| Containerization | Docker, Docker Compose |
| CI/CD | GitHub Actions |
| Container Registry | Docker Hub |
| Cloud Deployment | Digital Ocean |

---

## Notes

- Raw dataset files are **not committed** to this repository due to file size. See [Load the Dataset](#3-load-the-dataset) for setup instructions.
- The `ML/data/processed/` directory must be populated before the app will function. Use the Google Drive link (Option A) for the fastest setup.
- `.env` is excluded from version control. Use `env.example` as the template.
