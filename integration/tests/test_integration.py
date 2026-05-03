"""Tests for the CatCh integration router."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.integration import router

application = FastAPI()
application.include_router(router)
client = TestClient(application)


def test_health():
    """Health endpoint returns an ok response."""

    response = client.get("/integration/health")
    assert response.status_code == 200
