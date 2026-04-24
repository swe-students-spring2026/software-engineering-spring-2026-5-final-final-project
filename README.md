# Final Project

![API CI/CD badge](https://github.com/<owner>/<repo>/actions/workflows/apis.yml/badge.svg)
![Frontend CI/CD badge](https://github.com/<owner>/<repo>/actions/workflows/frontend.yml/badge.svg)

An exercise to practice software development teamwork, database integration, containers, deployment, and CI/CD pipelines.

## Overview

This repository is...

- MongoDB as the backing database
- `apis`, a Flask-based API service
- `frontend`, a Flask-based web frontend

The API service exposes a `/health` endpoint and the frontend service serves a simple landing response. Both custom services run in their own containers and are orchestrated with Docker Compose alongside MongoDB.

## Container Images

Replace the placeholder links below with the published Docker Hub repositories for each custom subsystem.

- API image: `https://hub.docker.com/r/<dockerhub-namespace>/<api-image-name>`
- Frontend image: `https://hub.docker.com/r/<dockerhub-namespace>/<frontend-image-name>`

## Team

- [Robin Chen](https://github.com/localhost433)
- [Minho Eune](https://github.com/minhoeune)
- 
- 
- 

## Requirements

- Docker Desktop or the Docker Engine with Docker Compose
- Python 3.14 only if you want to run the Flask apps outside containers
- A MongoDB account is not required for local development because the database runs in a container

## Configuration

1. Copy the example environment file into place:

 ```bash
 cp .env.example .env
 ```

1. Update the values in `.env` before starting the stack.

2. At minimum, change `MONGO_INITDB_ROOT_PASSWORD` from the dummy value in the example file.

The current example configuration lives in [`.env.example`](.env.example).

### Environment Variables

The Compose file expects the following values:

- `PYTHON_IMAGE_TAG`
- `MONGO_IMAGE_TAG`
- `MONGO_CONTAINER_NAME`
- `API_CONTAINER_NAME`
- `FRONTEND_CONTAINER_NAME`
- `MONGO_INITDB_ROOT_USERNAME`
- `MONGO_INITDB_ROOT_PASSWORD`
- `MONGO_DB_NAME`
- `MONGO_HOST`
- `MONGO_PORT`
- `MONGO_INTERNAL_PORT`
- `MONGO_AUTH_SOURCE`
- `API_PORT`
- `API_INTERNAL_PORT`
- `FRONTEND_PORT`
- `FRONTEND_INTERNAL_PORT`

## Run Locally

1. Install Docker Desktop on your platform.
2. Clone the repository.
3. Create `.env` from `.env.example` and update the secrets.
4. Start the stack:

 ```bash
 docker compose up --build
 ```

5. Open the services in your browser:

- Frontend: `http://localhost:3000`
- API health check: `http://localhost:8000/health`
- MongoDB: `localhost:27017`

To stop the stack, run:

```bash
docker compose down
```

## Database Setup

MongoDB starts with an empty data volume the first time you bring the stack up. There is currently no starter data import script, so no additional seeding step is required.

If you later add starter data, document the import command here and commit the seed file or script alongside it.

## Development Notes

- `apis/app/main.py` contains the API entrypoint.
- `frontend/app/main.py` contains the frontend entrypoint.
- Each subsystem has its own `Dockerfile` and is built independently by Compose.
- The API service reads `MONGO_URI`, `MONGO_DB_NAME`, and `API_INTERNAL_PORT` from the environment.
- The frontend service reads `FRONTEND_INTERNAL_PORT` from the environment.

## CI/CD

Each custom subsystem should have its own GitHub Actions workflow that runs on pushes and pull requests to `main` or `master`, builds the image, runs tests, publishes to Docker Hub, and deploys the online service when appropriate.

When those workflows are added, link them here and keep the badges above in sync.
