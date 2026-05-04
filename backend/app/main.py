from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routers import spotify
from app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    start_scheduler()
    yield
    # shutdown
    stop_scheduler()


app = FastAPI(lifespan=lifespan)
app.include_router(spotify.router)