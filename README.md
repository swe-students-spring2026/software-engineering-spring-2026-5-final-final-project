[![.github/workflows/web-app-ci.yml](https://github.com/swe-students-spring2026/5-final-treehopper_colony/actions/workflows/web-app-ci.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-treehopper_colony/actions/workflows/web-app-ci.yml)
# Final Project

An exercise to put to practice software development teamwork, subsystem communication, containers, deployment, and CI/CD pipelines. See [instructions](./instructions.md) for details.


## Local Development Setup for Web App

### 1. Configure Environment Variables

1. Navigate to the `web_app` directory.
2. Duplicate the `env.example` file and rename the copy to exactly `.env` [2].
3. Ensure the `.env` file contains the following local database configuration [2, 3]:
   ```text
   MONGO_URI=mongodb://localhost:27017
   DB_NAME=task_reminder_db
4. run in terminal: pipenv install
5. run in terminal: pipenv run python app.py
