![Web APP CI](https://github.com/swe-students-spring2026/5-final-lacewing_squad/actions/workflows/web-app.yml/badge.svg)
![Machine Learning Client CI](https://github.com/swe-students-spring2026/5-final-lacewing_squad/actions/workflows/ml-client.yml/badge.svg)

# Lacewing — Task Tracker

## Container Imagines

[ML Client](https://hub.docker.com/r/eddy61676/lacewing_squad_ml_client)

[Web App](https://hub.docker.com/r/eddy61676/lacewing_squad_web_app)

## App Description

A task tracker that helps students manage assignments by automatically predicting difficulty, priority, and estimated hours using AI. Tasks are organized into overdue, due soon, upcoming, and completed categories.

[App Link](http://67.205.139.23:5001/)

## Team Members

[Eddy Yue](https://github.com/YechengYueEddy)

## Running the Application

### Prerequisites

- Install and run [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Git](https://git-scm.com/)

### Step 1: Create the `.env` file

In the project root, create a `.env` file by copying the example:

```bash
cp env.example .env
```

Then fill in your values:

```env
MONGO_INITDB_ROOT_USERNAME=youruser
MONGO_INITDB_ROOT_PASSWORD=yourpassword
MONGO_DBNAME=mydb
MONGO_URI=mongodb://youruser:yourpassword@mongo:27017
GOOGLE_API_KEY=your-google-api-key
```

To get a **Google API key**:
- Go to [Google AI Studio](https://aistudio.google.com/) and sign in
- Click **Get API key**, then **Create API key**

### Step 2: Build and Start All Containers

```bash
docker-compose up --build
```

This starts all three containers:
- **Web App** at `http://localhost:5001`
- **ML Client** at `http://localhost:5002`
- **MongoDB** at `localhost:27017`

### Step 3: Use the App

Open `http://localhost:5001` in your browser, register an account, and start adding tasks.

### Stopping the App

```bash
docker-compose down
```

To stop and remove all data:

```bash
docker-compose down -v
```
