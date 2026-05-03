"""Integration service routes for shared CatCh contracts."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/integration", tags=["integration"])


class ServiceEndpoint(BaseModel):
    """Service ownership entry returned by the integration service map."""

    service: str
    base_url: str
    owns: list[str]


@router.get("/health")
async def health():
    """Return integration service health information."""

    return {"status": "integration ok", "service": "integration"}


@router.get("/product-rules")
async def product_rules():
    """Return shared product rules for CatCh services and frontends."""

    return {
        "name": "CatCh: Code, Fish, and Learn",
        "roles": {
            "kitten": {
                "description": "Student gameplay user",
                "uses_tokens": True,
                "uses_fishing_chances": True,
                "leaderboards": ["token", "aquarium_collection"],
            },
            "cat": {
                "description": "Teacher and problem creator",
                "uses_tokens": False,
                "uses_fishing_chances": False,
                "leaderboards": [],
            },
        },
        "aquarium": {
            "replaces": "medal wall",
            "progress_basis": "unique fish species collected / current fish dataset size",
            "tracks_quantity": True,
            "dynamic_interactions": [
                "swimming fish",
                "click for details",
                "hover for name and rarity",
                "filter by rarity",
                "sort by quantity",
            ],
        },
        "pond_ranking": "support votes - not-support votes",
        "default_public_pond": "CatCh Fish Pond",
    }


@router.get("/service-map", response_model=list[ServiceEndpoint])
async def service_map():
    """Return service ownership and local development endpoints."""

    return [
        ServiceEndpoint(
            service="auth-service",
            base_url="http://localhost:8002",
            owns=["email verification", "JWT", "cat/kitten role claims"],
        ),
        ServiceEndpoint(
            service="teacher-service",
            base_url="http://localhost:8003",
            owns=[
                "cat fish pond management",
                "problem creation",
                "room code invitations",
            ],
        ),
        ServiceEndpoint(
            service="game-service",
            base_url="http://localhost:8000",
            owns=[
                "kitten gameplay",
                "fishing chances",
                "tokens",
                "marketplace",
                "aquarium",
            ],
        ),
        ServiceEndpoint(
            service="grader-service",
            base_url="http://localhost:8001",
            owns=["Judge0-style code checking adapter", "student submission verdicts"],
        ),
    ]


@router.get("/frontend-config")
async def frontend_config():
    """Return frontend feature flags and shared vocabulary."""

    return {
        "teacher": {
            "show_token_widgets": False,
            "primary_actions": [
                "create pond",
                "add problem",
                "send room code",
                "create assignment",
            ],
        },
        "kitten": {
            "show_token_widgets": True,
            "primary_actions": ["solve problem", "fish", "view aquarium", "trade fish"],
        },
        "renamed_features": {
            "medal_wall": "aquarium",
            "student": "kitten",
            "teacher": "cat",
            "classroom": "fish pond",
        },
    }
