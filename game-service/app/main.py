import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import aquarium, fishing, leaderboard, market, ponds, quiz, tokens

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR_CANDIDATES = [
    Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else None,
    SERVICE_ROOT / "data",
    REPO_ROOT / "data",
]
DATA_DIR = next(
    (path for path in DATA_DIR_CANDIDATES if path is not None and path.exists()),
    SERVICE_ROOT / "data",
)
FISH_IMAGES_DIR = DATA_DIR / "fish_images"


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
    app.include_router(market.router)
    app.include_router(aquarium.router)
    app.include_router(leaderboard.router)
    app.include_router(ponds.router)
    app.include_router(tokens.router)
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
