# StudyCast

[![log github events](https://github.com/swe-students-spring2026/5-final-slimmy_snakes/actions/workflows/event-logger.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-slimmy_snakes/actions/workflows/event-logger.yml)
[![CI (planner web)](https://github.com/swe-students-spring2026/5-final-slimmy_snakes/actions/workflows/planner-web-ci.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-slimmy_snakes/actions/workflows/planner-web-ci.yml)
[![CI (study session service)](https://github.com/swe-students-spring2026/5-final-slimmy_snakes/actions/workflows/study-session-service-ci.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-slimmy_snakes/actions/workflows/study-session-service-ci.yml)

StudyCast is a containerized academic planner with a Flask web app, a study-session focus service, and MongoDB storage. It helps students manage to-do items, exams, preparation plans, calendar/weather context, and focus-session feedback.

## Subsystems

- `planner-web`: Flask web dashboard for authentication, tasks, exams, preparation planning, calendar/weather views, and study-session controls.
- `study-session-service`: Flask API for starting/ending study sessions and classifying distraction risk.
- `mongodb`: MongoDB database container with starter initialization data.

## Run Locally

```powershell
docker compose up --build
```

Then open:

```text
http://localhost:5001
```

## Run Tests

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Run each subsystem with the required 80% coverage gate:

```powershell
cd planner-web
..\.venv\Scripts\python.exe -m pytest --cov=app --cov=calendar_weather --cov-report=term-missing --cov-fail-under=80
```

```powershell
cd study-session-service
..\.venv\Scripts\python.exe -m pytest --cov=app --cov=detector --cov-report=term-missing --cov-fail-under=80
```

The same coverage checks run in GitHub Actions, so the README badges turn green after the workflows pass on GitHub.
