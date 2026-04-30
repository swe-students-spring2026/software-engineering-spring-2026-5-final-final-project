# Final Project

An exercise to put to practice software development teamwork, subsystem communication, containers, deployment, and CI/CD pipelines. See [instructions](./instructions.md) for details.

## Run Locally

1. Create your env file:
   - `cp .env.example .env`
2. Edit `.env`
3. Build and start all containers:
   - `docker compose up --build -d`
4. Open:
   - Web app: [http://localhost:3000](http://localhost:3000)
5. Stop containers:
   - `docker compose down`
