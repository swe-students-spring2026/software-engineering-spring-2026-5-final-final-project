# FlakeMate

[![invite_adjuster CI](https://github.com/swe-students-spring2026/5-final-flake_mates-1/actions/workflows/invite_adjuster.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-flake_mates-1/actions/workflows/invite_adjuster.yml)
[![web_app CI](https://github.com/swe-students-spring2026/5-final-flake_mates-1/actions/workflows/web_app.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-flake_mates-1/actions/workflows/web_app.yml)
[![log github events](https://github.com/swe-students-spring2026/5-final-flake_mates-1/actions/workflows/event-logger.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-flake_mates-1/actions/workflows/event-logger.yml)

## Project Description

This project is a containerized event sharing application built with three connected subsystems: a Flask web app, a backend invite adjuster, and a MongoDB database.

The web app allows users to create an account, sign in, and create and share events with other users. It also allows the hosts of events to report how late each attendee is to the event. These lateness reports are then turned into a lateness score for each user, which is then used to shift event times for certain users. For example, is a user is typically late, their events will appear to be scheduled earlier, in order to push them to be on time. The database stores user data and event records, which allows the web app and backend invite adjuster to access the same data.

This repository is organized as a monorepo. The `web_app` directory contains the Flask application. The `invite_adjuster` directory contains the backend invite adjuster algorithm. MongoDB runs in its own container through Docker Compose.

## Container Images

- [web-app](https://hub.docker.com/repository/docker/chasecvitale/web-app/general)
- [invite-adjuster](https://hub.docker.com/repository/docker/chasecvitale/invite-adjuster/general)

## Team Members

- [Chase](https://github.com/chasecvitale)
- [Ethan](https://github.com/ethantyr)
- [Laiyi](https://github.com/laiEEEEEEE)
- [Lan](https://github.com/lpn4939-web)
- [Kara](https://github.com/cynikjinchen)

## Main Features

- User account creation
- User login
- Event creation
- Event sharing
- Accepting or declining an event invitation
- Custom event start times based on previous lateness
- MongoDB-backed storage
- Multi-container deployment using Docker Compose

## Environment Variables

This project does not require any environment variables for basic operation. All configuration is handled in `docker-compose.yml`.

## Database Setup

The database starts empty. To create your first user:

1. Open `http://127.0.0.1:5002/create-account`
2. Enter your name, phone number, and password
3. Sign in with your phone number and password

All necessary database collections are created automatically as you use the application.

## How to Configure and Run the Project

Before running the project, make sure the following are installed on your machine:

- Docker
- Docker Compose

You can check this with:

```bash
docker --version
docker compose version

```

From the root of the repository, run:

```bash
docker compose build
docker compose up

```
Then open this URL in your browser: `http://127.0.0.1:5002/`

After creating an account and signing in, you can start exploring the main features of the app, including creating and sharing events, and accepting and declining event invitations.
