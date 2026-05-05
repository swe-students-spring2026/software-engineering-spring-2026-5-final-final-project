[![CI/CD (Web App)](https://github.com/swe-students-spring2026/5-final-vaquita_porposies/actions/workflows/webapp-ci-cd.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-vaquita_porposies/actions/workflows/webapp-ci-cd.yml)
[![CI/CD (Machine Learning)](https://github.com/swe-students-spring2026/5-final-vaquita_porposies/actions/workflows/mi-ci-cd.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-vaquita_porposies/actions/workflows/mi-ci-cd.yml)
[![CI/CD (Database / Backend)](https://github.com/swe-students-spring2026/5-final-vaquita_porposies/actions/workflows/db-ci-cd.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-vaquita_porposies/actions/workflows/db-ci-cd.yml)

# Final Project

Our project contains a Python-based meme generation application built as a monorepo with 3 subsystems: a web app, a backend/database support subsystem using MongoDB, and a machine learning summarizer + meme generator.

## Team

- [Adam S](https://github.com/adamsolimancs/)
- [Ermuun B](https://github.com/ermuun0930/)
- [Milan E](https://github.com/MilanEngineer)
- [Tsengelmurun](https://github.com/murnbn)
- [Yuliang Liu](https://github.com/yl11529)

## Subsystems

- `web-app/`: Python web application code, templates, static assets, MongoDB integration, tests, and Dockerfile.
- `backend/`: Backend/database support logic for article fetching, summary/caption assembly, storage document construction, tests, and Dockerfile.
- `ml/`: Machine learning / meme generation helper code for building memegen image responses, tests, and Dockerfile.
- MongoDB: Required database service used by the web application for generated meme history.

## Docker Images

The CI/CD workflows publish images to Docker Hub using the configured `DOCKERHUB_USERNAME` secret:

- Web app: `DOCKERHUB_USERNAME/project5-web-app`
- Machine learning: `DOCKERHUB_USERNAME/project5-ml`
- Backend/database: `DOCKERHUB_USERNAME/project5-db`

Replace `DOCKERHUB_USERNAME` with the Docker Hub account configured in GitHub Actions. (graders please see .env on discord)

## Local Setup

Install Python 3.10, Docker, and Pipenv.

Create a local environment file from the example:

```sh
cp .env.example .env
```

The example contains:

```sh
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5.4-mini
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=meme_generator
MONGODB_COLLECTION_NAME=generated_memes
```

Run the full local stack from the repository root with Docker Compose:

```sh
docker compose up --build
```

This builds and starts the web app, backend, machine learning subsystem, and MongoDB. The web app is available at `http://localhost:5000`.

The `.env.example` MongoDB URI uses `localhost` for host-machine development. The Compose file overrides it inside containers with `mongodb://mongodb:27017`, which is the correct service name on the Docker Compose network.

Stop the stack with:

```sh
docker compose down
```

To also remove the local MongoDB volume created by Compose:

```sh
docker compose down -v
```

Install and test each Python subsystem:

```sh
cd web-app
pipenv install --dev --python 3.10
pipenv run pytest --cov=app --cov-report=term-missing --cov-fail-under=80
```

```sh
cd backend
pipenv install --dev --python 3.10
pipenv run pytest --cov=app --cov-report=term-missing --cov-fail-under=80
```

```sh
cd ml
pipenv install --dev --python 3.10
pipenv run pytest --cov=meme --cov-report=term-missing --cov-fail-under=80
```

## Docker Builds

Build the subsystem containers from the repository root:

```sh
docker build -t project5-web-app:local web-app
docker build -t project5-ml:local ml
docker build -t project5-db:local backend
```

## CI/CD

GitHub Actions workflows live in `.github/workflows/`:

- `webapp-ci-cd.yml`
- `mi-ci-cd.yml`
- `db-ci-cd.yml`

Each workflow runs on pushes and pull requests targeting `main`. The workflows install dependencies, run tests, build Docker images, and push images to Docker Hub on pushes when these repository secrets are configured:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

## Database Seeding

No required starter data or seed script is currently included. MongoDB collections are created as the application writes generated meme history.
