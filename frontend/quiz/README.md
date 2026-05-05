# quiz-frontend

Minimal React + Vite + TypeScript frontend for the leetcode quiz module. Phase 1 MVP: lists problems, lets you write code in a Monaco editor, submits to game-service, alerts pass/fail. No login, no fishing animation, no leaderboard.

## Run locally

```
cd frontend/quiz
npm install
npm run dev
```

Opens on http://localhost:5173.

`game-service` must be running on http://localhost:8000 (the default `VITE_GAME_SERVICE_URL`). To point at a different backend:

```
VITE_GAME_SERVICE_URL=http://localhost:8000 npm run dev
```

## Build

```
npm run build
```

Produces static files in `dist/` ready to be served by nginx.

## Notes

`src/types.ts` mirrors the Pydantic models in `game-service/app/models.py`. If the backend models change, update both.

This is the quiz module's frontend. Sibling modules (fishing, market, leaderboard) live next to it under `frontend/`. The team will decide later whether to merge them into a single React app or keep them separate and combine via nginx routing.
