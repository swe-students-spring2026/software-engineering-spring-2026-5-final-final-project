"""Teacher-created pond routes consumed by teacher-service."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
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


class UpdatePondProblemRequest(BaseModel):
    """Request body for editing a teacher-created problem."""

    cat_id: str
    title: str
    prompt: str
    starter_code: str = ""
    reference_solution: str
    test_code: str
    topic: Optional[str] = None
    fishing_reward: int = Field(default=1, ge=0)


class JoinPrivatePondRequest(BaseModel):
    """Request body for a kitten joining a private pond by room code."""

    user_id: str
    room_code: str


def repo() -> Repository:
    """Return the configured repository."""

    return get_repository()


def slugify(value: str) -> str:
    """Create a lowercase identifier fragment."""

    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return slug or "pond"


def ensure_teacher_owns_pond(pond: dict, cat_id: str) -> None:
    """Reject teacher mutations for classrooms owned by another cat."""

    if pond.get("cat_id") != cat_id:
        raise HTTPException(status_code=403, detail="cat does not own this pond")


def problem_updates_from_payload(payload: UpdatePondProblemRequest) -> dict:
    """Map editable teacher fields into the runtime problem schema."""

    return {
        "title": payload.title,
        "instructions": payload.prompt,
        "starter_code": payload.starter_code,
        "topic": payload.topic,
        "test_code": payload.test_code,
        "solution_code": payload.reference_solution,
        "fishing_reward": payload.fishing_reward,
    }


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
        "room_code": payload.room_code.strip().upper() if payload.room_code else None,
        "cat_id": payload.cat_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "problem_ids": [],
        "member_user_ids": [],
    }
    return repository.create_pond(pond)


@router.get("/teacher/{cat_id}")
async def list_teacher_ponds(
    cat_id: str,
    repository: Repository = Depends(repo),
):
    """Return classrooms created by one teacher."""

    return repository.list_teacher_ponds(cat_id)


@router.post("/private/join")
async def join_private_pond(
    payload: JoinPrivatePondRequest,
    repository: Repository = Depends(repo),
):
    """Join a private pond using its room code."""

    try:
        return repository.join_private_pond(payload.user_id, payload.room_code)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{pond_id}/problems")
async def list_pond_problems(
    pond_id: str,
    repository: Repository = Depends(repo),
):
    """Return teacher-created problems inside a fish pond."""

    if repository.get_pond(pond_id) is None:
        raise HTTPException(status_code=404, detail="pond not found")
    return repository.list_pond_problems(pond_id)


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
    ensure_teacher_owns_pond(pond, payload.cat_id)
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


@router.put("/{pond_id}/problems/{problem_id}")
async def update_problem(
    pond_id: str,
    problem_id: str,
    payload: UpdatePondProblemRequest,
    repository: Repository = Depends(repo),
):
    """Update a teacher-authored problem inside a fish pond."""

    pond = repository.get_pond(pond_id)
    if pond is None:
        raise HTTPException(status_code=404, detail="pond not found")
    ensure_teacher_owns_pond(pond, payload.cat_id)
    try:
        problem = repository.update_pond_problem(
            pond_id,
            problem_id,
            problem_updates_from_payload(payload),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "updated", "pond_id": pond_id, "problem": problem}


@router.delete("/{pond_id}/problems/{problem_id}")
async def delete_problem(
    pond_id: str,
    problem_id: str,
    cat_id: str,
    repository: Repository = Depends(repo),
):
    """Delete a teacher-authored problem from a fish pond."""

    pond = repository.get_pond(pond_id)
    if pond is None:
        raise HTTPException(status_code=404, detail="pond not found")
    ensure_teacher_owns_pond(pond, cat_id)
    try:
        repository.delete_pond_problem(pond_id, problem_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted", "pond_id": pond_id, "problem_id": problem_id}
