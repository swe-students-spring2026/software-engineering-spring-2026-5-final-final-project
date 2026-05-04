from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import create_indexes
from app.routers import spotify
from app.services.scheduler import start_scheduler, stop_scheduler
# from app.routers import auth, users, feed, likes, matches  # uncomment as merged


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_indexes()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(spotify.router)
# app.include_router(auth.router)     # Jack
# app.include_router(users.router)    # Jack
# app.include_router(feed.router)     # Sarah
# app.include_router(likes.router)    # Sarah
# app.include_router(matches.router)  # Sarah
