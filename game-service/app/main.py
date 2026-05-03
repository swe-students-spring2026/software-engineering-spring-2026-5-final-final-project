from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import fishing, quiz

REPO_ROOT = Path(__file__).resolve().parents[2]
FISH_IMAGES_DIR = REPO_ROOT / "data" / "fish_images"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Game Service",
        description="quiz, fishing, market and leaderboard for Fish_Likes_Cat",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(quiz.router)
    app.include_router(fishing.router)
    app.mount(
        "/fish_images",
        StaticFiles(directory=FISH_IMAGES_DIR),
        name="fish_images",
    )

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok", "service": "game-service"}

    return app


app = create_app()
