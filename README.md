# Bloom Bugs: Mood Music Recommender

[![Web App CI/CD](https://github.com/swe-students-spring2026/5-final-bloom_bugs/actions/workflows/web-app.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-bloom_bugs/actions/workflows/web-app.yml)
[![ML Client CI/CD](https://github.com/swe-students-spring2026/5-final-bloom_bugs/actions/workflows/ml-client.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-bloom_bugs/actions/workflows/ml-client.yml)
[![Event Logger](https://github.com/swe-students-spring2026/5-final-bloom_bugs/actions/workflows/event-logger.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-bloom_bugs/actions/workflows/event-logger.yml)

## 📌 Project Description
**Bloom Bugs** is an intelligent, context-aware music recommendation web application. By taking a user's current mood and their geographical location (to fetch real-time weather data), our Machine Learning subsystem intelligently curates a customized Spotify playlist that perfectly matches their vibe. 

This project is built using a microservices architecture with three distinct subsystems:
1. **Web App (Flask)**: Handles user authentication via Spotify, manages user sessions, and serves the frontend UI.
2. **ML Client (FastAPI)**: A machine learning API service that integrates with the Gemini API to analyze mood and weather, returning optimized music track recommendations.
3. **MongoDB**: A NoSQL database subsystem that persistently stores user search history and saved playlists.

---

## 🐳 DockerHub Images
You can pull the container images for our custom subsystems directly from DockerHub:
- **Web App**: [Link to Web App DockerHub Image](https://hub.docker.com/r/hy2484/moodify-web)
- **ML Service**: [Link to ML Service DockerHub Image](https://hub.docker.com/r/hy2484/moodify-ml)

---

## 👥 Meet the Team
- [Ami Bal (asb9823)](https://github.com/asb9823)
- [Hanlin Yan (hanlinyan-dev)](https://github.com/hanlinyan-dev)
- [Qingyue Zhang (Kairiszqy)](https://github.com/Kairiszqy)
- [Steve Yoo (seonghoyu11)](https://github.com/seonghoyu11)
- [Inoo Jung (ij2298-oss)](https://github.com/ij2298-oss)

---

## 🚀 How to Configure & Run the Project

Follow these exact instructions to set up the project locally on any platform.

### 1. Prerequisites
- [Docker & Docker Compose](https://www.docker.com/products/docker-desktop/) installed on your machine.
- A Spotify Developer account (for API credentials).
- Python 3.10+ (for running the database seed script).

### 2. Environment Variables Setup (Crucial!)
Security is a priority, so secret configuration files are not included in the version control repository. You must create them manually before running the application.

1. Locate the `.env.example` file in the root of the repository.
2. Copy the contents of `.env.example` to create a **single new file** named `.env` in the **root directory** of the project:
   ```bash
   cp .env.example .env
   ```
3. Open the `.env` file and fill in the dummy data with your actual API keys:
   - `SPOTIFY_CLIENT_ID` & `SPOTIFY_CLIENT_SECRET`: Obtain these from the Spotify Developer Dashboard.
   - `GEMINI_API_KEY`: Obtain from Google AI Studio.
   - `OPENWEATHER_API_KEY`: Obtain from OpenWeatherMap.
   - `SECRET_KEY`: Set to any random string for Flask session security.
   - `MONGO_URI`: Keep as `mongodb://mongo:27017/moodmusic` to use the local dockerized MongoDB container.

### 3. Build and Run the Containers
Once your `.env` file is in place at the root directory, open your terminal at the root of the project and run:
```bash
docker-compose up --build -d
```
This command will build the custom subsystem images and start the Web App, ML Service, and MongoDB containers in the background. 

Wait about 10-15 seconds for all services to initialize. The services will be accessible at:
- **Web App**: http://localhost:5000
- **ML Service**: http://localhost:8000

### 4. Import Starter Data (Database Seeding)
To verify that the database integration is working and to populate it with dummy session history and playlists, run the seed script.

In your terminal, run the following command from the root directory:
```bash
pip install pymongo python-dotenv
python seed_data.py
```

If successful, you will see output indicating that session records and playlists have been inserted into the `moodmusic` database. When you log into the Web App, you should now see populated history.
