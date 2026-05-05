"""FastAPI entry point for the CatCh integration service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.integration import router as integration_router


def create_app() -> FastAPI:
    """Create and configure the integration FastAPI app."""

    application = FastAPI(
        title="Integration Service",
        description="CatCh cross-service contracts and frontend configuration",
        version="0.2.0",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:5175",
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(integration_router)
    return application


app = create_app()
