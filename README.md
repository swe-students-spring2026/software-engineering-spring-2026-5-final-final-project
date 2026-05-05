# Mood Music: Final Project

[![ML Client CI/CD](https://github.com/swe-students-spring2026/5-final-bloom_bugs/actions/workflows/ml-client.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-bloom_bugs/actions/workflows/ml-client.yml)
[![Web App CI/CD](https://github.com/swe-students-spring2026/5-final-bloom_bugs/actions/workflows/web-app.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-bloom_bugs/actions/workflows/web-app.yml)
[![Event Logger CI/CD](https://github.com/swe-students-spring2026/5-final-bloom_bugs/actions/workflows/event-logger.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-bloom_bugs/actions/workflows/event-logger.yml)

## Description

**Moodify** is an interactive, multi-agent recommendation system that suggests Spotify playlists based on a combination of a user's current mood and their local weather. The system consists of an interactive front-end web application, a machine learning backend service, and a MongoDB database to persist user sessions and feedback for future model tuning. 

When a user submits their mood, the ML service leverages language models (like Claude/Gemini) to parse the text and weather data into an audio profile, which is then mapped to relevant tracks via the Spotify API.

### Container Images
The application is split into multiple containerized subsystems hosted on Docker Hub:
- [**ML Client**](https://hub.docker.com/r/hy2484/moodify-ml): A FastAPI backend for parsing mood and generating Spotify recommendations.
- [**Web App**](https://hub.docker.com/r/hy2484/moodify-web): A Flask-based interactive web UI.
- **MongoDB**: A standard database container for data persistence.

## Teammates

- [Ami Bal (asb9823)](https://github.com/asb9823)
- [Inoo Jung (ij2298-oss)](https://github.com/ij2298-oss)
- [Hanlin Yan (hanlinyan-dev)](https://github.com/hanlinyan-dev)
- [Steve Yoo (seonghoyu11)](https://github.com/seonghoyu11)
- [Qingyue Zhang (Kairiszqy)](https://github.com/Kairiszqy)

## Setup and Configuration

Follow these instructions to run the project locally on any platform.

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Python 3.10+ (for running the database seed script)

### 1. Environment Variables Configuration

The project relies on a `.env` file to store secret API keys securely. This file is not included in version control.

1. Copy the provided `.env.example` file to create your own local `.env` file at the root of the repository:
   ```bash
   cp .env.example .env
   ```
2. Open the `.env` file and replace the dummy values with your actual API keys:
   - `SECRET_KEY`: A random secret key for Flask sessions.
   - `SPOTIFY_CLIENT_ID` & `SPOTIFY_CLIENT_SECRET`: Your Spotify Developer app credentials.
   - `GEMINI_API_KEY`: API key for Gemini.
   - `OPENWEATHER_API_KEY`: API key for OpenWeather.

### 2. Running the Application

Once your `.env` file is properly configured, you can launch all the subsystems using Docker Compose.

1. Open a terminal in the root directory of the project.
2. Build and run the containers:
   ```bash
   docker-compose up --build
   ```
3. The services will be accessible at:
   - **Web App**: http://localhost:5000
   - **ML Service**: http://localhost:8000

### 3. Importing Starter Data (Database Seeding)

To ensure the system operates correctly and has initial dummy sessions/playlists, you need to seed the MongoDB database.

1. Keep the Docker containers running in the background.
2. Open a new terminal instance.
3. Ensure you have the required Python packages installed:
   ```bash
   pip install pymongo python-dotenv
   ```
4. Run the data seeding script:
   ```bash
   python seed_data.py
   ```
   You should see output confirming that session and playlist records were inserted into the database.
