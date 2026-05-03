# NYC 311 Smart Spot Finder

[![CI](https://github.com/swe-students-spring2026/5-final-rove_beetle_crew/actions/workflows/test.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-rove_beetle_crew/actions/workflows/test.yml)

---

## About

**NYC 311 Smart Spot Finder** is a web application that helps New Yorkers discover the best spots in the city based on what they're looking for. Users can search for places using natural-language prompts like *"find me a safe spot"* or *"suggest a quiet study spot"*  — and the app responds with real, data-backed location recommendations.

Under the hood, the app uses the open-source [NYC 311 Service Requests dataset](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9/about_data) and the [NYC Facilities Database](https://data.cityofnewyork.us/City-Government/Facilities-Database/ji82-xba5/about_data) to understand neighborhood conditions and match them to user intent via a machine learning model.

---

## Architecture

The project is a monorepo composed of **2 subsystems**:

```

                          Monorepo

             
     web-app/              ML/
    (Flask frontend        (ML Engine —
     + ML integration)     Python library)


    Planned: Docker Hub + Digital Ocean deployment

```

| Subsystem | Description |
|-----------|-------------|
| `web-app/` | User-facing Flask web application. Accepts natural-language prompts and displays recommended spots on a map. The ML engine (`ML/src/`) is imported directly into this service. |
| `ML/` | Python ML library that processes 311 and Facilities data, scores locations via semantic search and custom clustering, and returns ranked recommendations. |

---

## Container Images

> **TODO:** Docker image builds and Docker Hub publishing are planned but not yet configured. The `web-app/Dockerfile` is a placeholder.

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

- Python 3.10+
- [Git](https://git-scm.com/)
- [Docker](https://docs.docker.com/get-docker/) (v24+) *(planned for containerized deployment)*

---

### 1. Clone the Repository

```bash
git clone https://github.com/swe-students-spring2026/5-final-rove_beetle_crew.git
cd 5-final-rove_beetle_crew
```

---

### 2. Install Dependencies

```bash
pip install -r requirement.txt
```

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
pip install -r requirement.txt
python ML/src/preprocess.py
```

Output files will be written to `ML/data/processed/`.

---

### 4. Run the Web App

The web app imports the ML engine directly, so `ML/src/` must be on the Python path:

```bash
PYTHONPATH=ML/src python web-app/app.py
```

| Service    | URL                       |
|------------|---------------------------|
| Web App    | http://localhost:5000     |

> **Note:** Docker Compose support is planned but not yet available.

---

### 5. Test the ML Engine Locally

You can test the ML recommendation engine directly by editing the query inside the `main()` function in `ML/src/main.py`:

```python
# ML/src/main.py — modify this to test different prompts
query = "a quiet place to study where it's also safe"
```

Then run:

```bash
pip install -r requirement.txt
cd ML/src
python main.py
```

---

## Repository Structure

```
.
 web-app/                    # Flask frontend + ML integration
    app.py
    templates/
    static/
    Dockerfile               # Placeholder — not yet configured

 ML/                         # ML recommendation engine (Python library)
    src/
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

 tests/                      # Test suite
    test_basic.py
    test_preprocess.py

 .github/
    workflows/
        test.yml            # CI pipeline (runs pytest)

 pyproject.toml              # Pytest configuration
 requirement.txt             # Python dependencies
 README.md
```

---

## Running Tests

```bash
pip install -r requirement.txt
pytest
```

The `pyproject.toml` configures pytest to discover tests under the `tests/` directory.

---

## CI/CD Pipeline

The project uses a single GitHub Actions workflow (`.github/workflows/test.yml`), triggered on every push or pull request to `main`.

| Workflow File | Trigger                     |
|---------------|-----------------------------|
| `test.yml`    | Push or PR to `main`        |

The workflow:
1. Installs Python and test dependencies (`pytest`, `pandas`, `pytest-cov`)
2. Runs the full test suite with `pytest`

> **Planned:** Docker image builds, Docker Hub publishing, and Digital Ocean deployment are not yet configured.

---

## Live Deployment

> **Coming soon.** Deployment to Digital Ocean is planned once Docker images are configured.

- **Web App**: *(update once deployed)*
- **ML Service**: *(update once deployed)*

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Flask, Jinja2, HTML/CSS/JS |
| ML Engine | Python, sentence-transformers, NumPy, pandas |
| Data Sources | NYC Open Data - 311 Service Requests & Facilities Database |
| Containerization | Docker *(planned)* |
| CI/CD | GitHub Actions |

---

## Notes

- Raw dataset files are **not committed** to this repository due to file size. See [Load the Dataset](#3-load-the-dataset) for setup instructions.
- The `ML/data/processed/` directory must be populated before the app will function. Use the Google Drive link (Option A) for the fastest setup.
- MongoDB and Docker Compose support are planned but not yet implemented in the current codebase.
