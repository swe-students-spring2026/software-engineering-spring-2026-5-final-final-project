[![Frontend CI](https://github.com/swe-students-spring2026/5-final-stonefly_ring/actions/workflows/frontend.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-stonefly_ring/actions/workflows/frontend.yml)
[![API CI](https://github.com/swe-students-spring2026/5-final-stonefly_ring/actions/workflows/api.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-stonefly_ring/actions/workflows/api.yml)
[![Database CI](https://github.com/swe-students-spring2026/5-final-stonefly_ring/actions/workflows/database.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-stonefly_ring/actions/workflows/database.yml)

# Software Engineering Final Project

# CostShare App

Living with roommates necessitates purchases for the whole room (paper towels, Brita filters, toilet paper, etc.). Tracking all those expenses is difficult, and not doing so risks some roommates paying more than others and feeling hard done by. Therefore, we made an application that tracks all expenses and properly assigns each roommate their proper share. 

## Team
- [Adam Shin](https://github.com/aus2003)
- [@username2](https://github.com/username2)
- [@username3](https://github.com/username3)
- [@username4](https://github.com/username4)
- [@username5](https://github.com/username5)

## Docker Container Images
[Subsystem 1 Image]()
[Subsystem 2 Image]()
[Subsystem 3 Image]()

## Configuration

### Environment Variables
[Insert example .env file]

### Database Setup

[Outline how to setup the database and whether it needs any initial data to run.]

## Running the Project

### Prerequisites

### With Docker Compose
```bash
# From the repo root
docker compose --build
docker compose up
```
## Backend Testing (Scoring-Critical)

These commands verify backend unit tests and code coverage for the API and database subsystems.

```bash
# from repo root
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r api/requirements.txt -r database/requirements.txt
python -m pip install pytest pytest-cov

# run backend tests
python -m pytest

# run backend coverage (API + database)
python -m pytest --cov=api --cov=database --cov-report=term-missing
```

## Starter Data (Database)

After the database is initialized, you can seed local starter data:

```bash
source .venv/bin/activate
python database/seed_data.py
```