"""FastAPI app for the CatCh market module."""

from fastapi import FastAPI

from market.app.routers.market import router


app = FastAPI(
    title="CatCh Market Module",
    description="Standalone marketplace module for local testing.",
    version="0.1.0",
)
app.include_router(router)
