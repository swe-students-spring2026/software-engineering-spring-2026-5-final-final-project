[![Tests](https://github.com/swe-students-spring2026/5-final-katydid_brigade/actions/workflows/tests.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-katydid_brigade/actions/workflows/tests.yml)
[![Event Logger](https://github.com/swe-students-spring2026/5-final-katydid_brigade/actions/workflows/event-logger.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-katydid_brigade/actions/workflows/event-logger.yml)

# Most Puzzling

Most Puzzling is a boggle word game where users answer a set of questions designed by other players, and if their responses match with another user's answers, the two get connected.

## Team Member

[Marcus Song](https://github.com/Marclous)

[Chen Chen](https://github.com/LoganHund)

[Chenyu (Ginny) Jiang](https://github.com/ginny1536)

[Bryce](https://github.com/blin03)

## Run the web app with Docker

Build and start the container:

```sh
docker compose up --build
```

Then open http://localhost:8000.

To stop the app, press `Ctrl+C`, then run:

```sh
docker compose down
```

You can also build and run without Compose:

```sh
docker build -t katydid-web-app .
docker run --rm -p 8000:8000 katydid-web-app
```
