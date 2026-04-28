# Potatoes

<!-- Insert CI test badges here -->

## Overview
An application that analyzes student feedback for professors using sentiment analysis, allowing users to join groups and filter reviews accordingly.

The system is built with a microservice-style architecture, including:
- a Flask-based web application
- a machine learning service for sentiment analysis
- a MongoDB database for data storage

## Features
- 🔍 Sentiment analysis on student reviews
- 👥 Group system for shared interests
- 🏫 View professor ratings and reviews
- ⭐ Filter reviews by group or user preferences
- ✍️ Add and manage your own reviews
---

## 👥 Team

- [Cary Ho](https://github.com/CakeOfThePans)
- [Albert Chen](https://github.com/azc9673)
- [Joy Song](https://github.com/pancake0003)
- [Suri Su](https://github.com/suri-zip)
- [Ruby Zhang](https://github.com/yz10113-tech)

---

## Option 1: Quick Start (Recommended)

### Prerequisites
- Docker Desktop installed and running

---

### Run the full system

```bash
docker compose up --build
```

Optional (background mode):

```bash
docker compose up --build -d
```

Stop everything:

```bash
docker compose down
```

Optional (Stop everything and remove volumes):

```bash
docker compose down -v
```

---

## Access the Services

- Web App → http://localhost:5000

---

## Option 2: Running Services Individually

### MongoDB

```bash
docker run --name mongodb -p 27017:27017 -e MONGO_INITDB_ROOT_USERNAME=admin -e MONGO_INITDB_ROOT_PASSWORD=secret -d mongo:latest
```

---

### Web App

```bash
docker build -t web-app ./web-app

docker run -p 5000:5000 --name web-app -e MONGO_URI="mongodb://admin:secret@host.docker.internal:27017/?authSource=admin" -e MONGO_DBNAME=potatoes -e SECRET_KEY=dev -e ML_SERVICE_URL=http://host.docker.internal:5001 web-app
```

---

### ML Client

```bash
docker build -t machine-learning-client ./machine-learning-client

docker run -p 5001:5001 --name machine-learning-client -e MONGO_URI="mongodb://admin:secret@host.docker.internal:27017/?authSource=admin" -e MONGO_DBNAME=potatoes machine-learning-client
```

---

## Option 3: Run Locally Without Docker (for Development)

### 1. Start MongoDB

```bash
docker run --name mongodb -p 27017:27017 -e MONGO_INITDB_ROOT_USERNAME=admin -e MONGO_INITDB_ROOT_PASSWORD=secret -d mongo:latest
```

---

### 2. Setup Web App

```bash
cd web-app

pip install pipenv

pipenv shell
```

Set environment variables. An example file named `env.example` is given. Copy this into a file named `.env`:

```bash
MONGO_URI="mongodb://admin:secret@localhost:27017/?authSource=admin"
MONGO_DBNAME=potatoes
SECRET_KEY=dev
ML_SERVICE_URL=http://machine-learning-client:5001
```

Run:

```bash
python app.py
```

---

### 3. Setup ML Client

```bash
cd machine-learning-client

pip install pipenv

pipenv shell
```

Set environment variables. An example file named `env.example` is given. Copy this into a file named `.env`:

```bash
MONGO_URI="mongodb://admin:secret@localhost:27017/?authSource=admin"
MONGO_DBNAME=potatoes
```

Run:

```bash
python client.py
```

---