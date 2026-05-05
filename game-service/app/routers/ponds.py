"""Teacher-created pond routes consumed by teacher-service."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db import get_repository
from app.db.repository import Repository

router = APIRouter(prefix="/ponds", tags=["ponds"])
PondVisibility = Literal["public", "private"]


class CreatePondRequest(BaseModel):
    """Request body for creating a fish pond."""

    cat_id: str
    name: str
    description: Optional[str] = None
    visibility: PondVisibility = "public"
    room_code: Optional[str] = None


class AddPondProblemRequest(BaseModel):
    """Request body for adding a teacher-created problem to a pond."""

    cat_id: str
    pond_id: str
    title: str
    prompt: str
    starter_code: str = ""
    reference_solution: str
    test_code: str
    topic: Optional[str] = None
    fishing_reward: int = Field(default=1, ge=0)


def repo() -> Repository:
    """Return the configured repository."""

    return get_repository()


def slugify(value: str) -> str:
    """Create a lowercase identifier fragment."""

    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return slug or "pond"


@router.post("")
async def create_pond(
    payload: CreatePondRequest,
    repository: Repository = Depends(repo),
):
    """Persist a public or private teacher-created fish pond."""

    pond_id = f"pond_{slugify(payload.name)}_{uuid.uuid4().hex[:6]}"
    pond = {
        "pond_id": pond_id,
        "name": payload.name,
        "description": payload.description,
        "visibility": payload.visibility,
        "room_code": payload.room_code,
        "cat_id": payload.cat_id,
        "created_at": datetime.utcnow().isoformat(),
        "problem_ids": [],
    }
    return repository.create_pond(pond)


@router.post("/{pond_id}/problems")
async def add_problem(
    pond_id: str,
    payload: AddPondProblemRequest,
    repository: Repository = Depends(repo),
):
    """Persist a teacher-authored judgeable problem inside a fish pond."""

    if payload.pond_id != pond_id:
        raise HTTPException(status_code=400, detail="pond_id path/body mismatch")
    pond = repository.get_pond(pond_id)
    if pond is None:
        raise HTTPException(status_code=404, detail="pond not found")
    problem_id = f"{pond_id}_{slugify(payload.title)}_{uuid.uuid4().hex[:6]}"
    problem = {
        "id": problem_id,
        "pond_id": pond_id,
        "visibility": pond["visibility"],
        "title": payload.title,
        "function_name": "solve",
        "instructions": payload.prompt,
        "starter_code": payload.starter_code,
        "difficulty": "teacher",
        "fishing_reward": payload.fishing_reward,
        "source": "teacher",
        "source_url": "",
        "topic": payload.topic,
        "test_code": payload.test_code,
        "solution_code": payload.reference_solution,
        "solution_explanation": "Teacher-provided reference solution.",
        "max_attempts": 5,
    }
    return {
        "status": "created",
        "pond_id": pond_id,
        "problem": repository.add_problem_to_pond(pond_id, problem),
    }
