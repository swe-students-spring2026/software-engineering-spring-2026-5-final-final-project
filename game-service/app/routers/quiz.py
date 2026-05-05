from typing import List

import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.db import get_repository
from app.db.repository import Repository
from app.grader_client import grader_client
from app.services import tokens as token_service
from app.models import (
    Problem,
    ProblemSummary,
    SubmitRequest,
    SubmitResponse,
    UncaughtProblem,
)

router = APIRouter(prefix="/quiz", tags=["quiz"])


class ResetQuizRequest(BaseModel):
    """Request body for resetting a completed pond problem list."""

    user_id: str
    problem_ids: List[str] = Field(default_factory=list)


def repo() -> Repository:
    return get_repository()


def summarize_problem(problem: dict, progress: dict) -> ProblemSummary:
    """Build a problem summary with per-user completion state."""

    state = progress.get(problem["id"], {})
    return ProblemSummary(
        id=problem["id"],
        title=problem["title"],
        difficulty=problem["difficulty"],
        fishing_reward=problem["fishing_reward"],
        completed=bool(state.get("completed", False)),
        exhausted=bool(state.get("exhausted", False)),
        attempts_used=int(state.get("attempts_used", 0)),
    )


@router.get("/problems", response_model=List[ProblemSummary])
async def list_problems(
    user_id: str = "",
    repository: Repository = Depends(repo),
):
    progress = (
        {
            attempt["problem_id"]: attempt
            for attempt in repository.list_problem_attempts(user_id)
        }
        if user_id
        else {}
    )
    return [
        summarize_problem(problem, progress) for problem in repository.list_problems()
    ]


@router.get("/channels/{user_id}")
async def list_channels(
    user_id: str,
    repository: Repository = Depends(repo),
):
    """Return public and private quiz channels visible to a kitten."""

    progress = {
        attempt["problem_id"]: attempt
        for attempt in repository.list_problem_attempts(user_id)
    }
    default_problems = [
        summarize_problem(problem, progress)
        for problem in repository.list_problems()
        if not problem.get("pond_id")
    ]
    public_channels = [
        {
            "pond_id": "catch_public",
            "name": "Main Pond",
            "pinned": True,
            "problems": default_problems,
        }
    ]
    public_channels.extend(
        {
            "pond_id": pond["pond_id"],
            "name": pond["name"],
            "pinned": False,
            "problems": [
                summarize_problem(problem, progress)
                for problem in repository.list_pond_problems(pond["pond_id"])
            ],
        }
        for pond in repository.list_public_ponds()
    )
    private_channels = [
        {
            "pond_id": pond["pond_id"],
            "name": pond["name"],
            "room_code": pond.get("room_code"),
            "problems": [
                summarize_problem(problem, progress)
                for problem in repository.list_pond_problems(pond["pond_id"])
            ],
        }
        for pond in repository.list_private_ponds(user_id)
    ]
    return {
        "public": public_channels,
        "private": private_channels,
    }


@router.get("/progress/{user_id}")
async def quiz_progress(
    user_id: str,
    repository: Repository = Depends(repo),
):
    """Return a kitten's per-problem attempt and completion state."""

    return {
        "user_id": user_id,
        "attempts": repository.list_problem_attempts(user_id),
    }


@router.post("/reset")
async def reset_quiz_attempts(
    payload: ResetQuizRequest,
    repository: Repository = Depends(repo),
):
    """Reset attempt state for the selected quiz list so it can be replayed."""

    if not payload.problem_ids:
        raise HTTPException(status_code=400, detail="problem_ids is required")
    repository.reset_problem_attempts(payload.user_id, payload.problem_ids)
    return {
        "status": "reset",
        "user_id": payload.user_id,
        "problem_ids": payload.problem_ids,
    }


@router.get("/problems/{problem_id}", response_model=Problem)
async def get_problem(problem_id: str, repository: Repository = Depends(repo)):
    p = repository.get_problem(problem_id)
    if p is None:
        raise HTTPException(status_code=404, detail=f"problem '{problem_id}' not found")
    # test_code stays server-side only
    return Problem(
        id=p["id"],
        title=p["title"],
        function_name=p["function_name"],
        instructions=p["instructions"],
        starter_code=p["starter_code"],
        difficulty=p["difficulty"],
        fishing_reward=p["fishing_reward"],
        source=p["source"],
        source_url=p["source_url"],
        max_attempts=p.get("max_attempts", 5),
    )


@router.post("/problems/{problem_id}/submit", response_model=SubmitResponse)
async def submit(
    problem_id: str,
    body: SubmitRequest,
    repository: Repository = Depends(repo),
):
    problem = repository.get_problem(problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail=f"problem '{problem_id}' not found")

    max_attempts = int(problem.get("max_attempts", 5))
    state = repository.get_attempt_state(body.user_id, problem_id)
    if state["completed"]:
        raise HTTPException(
            status_code=409,
            detail="problem already completed; no duplicate fishing reward granted",
        )
    if state["exhausted"]:
        return SubmitResponse(
            passed=False,
            tests_run=0,
            tests_passed=0,
            error_message="attempt limit already reached",
            attempts_used=state["attempts_used"],
            attempts_remaining=0,
            max_attempts=max_attempts,
            solution_revealed=True,
            solution_code=problem.get("solution_code"),
        )

    try:
        result = await grader_client.grade(
            student_code=body.code,
            test_code=problem["test_code"],
            language=body.language,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"grader-service unavailable: {exc.__class__.__name__}",
        ) from exc

    passed = bool(result.get("passed", False))

    repository.record_submission(
        user_id=body.user_id,
        problem_id=problem_id,
        passed=passed,
        code=body.code,
    )
    state = repository.record_problem_attempt(
        user_id=body.user_id,
        problem_id=problem_id,
        passed=passed,
        code=body.code,
        max_attempts=max_attempts,
    )

    granted = 0
    new_chances = None
    solution_revealed = False
    solution_code = None
    added_to_uncaught = False
    tokens_lost = 0
    if passed:
        granted = problem["fishing_reward"]
        new_chances = repository.add_fishing_chances(body.user_id, granted)
    elif state["exhausted"]:
        solution_revealed = True
        solution_code = problem.get("solution_code")
        added_to_uncaught = repository.add_uncaught_problem(
            user_id=body.user_id,
            problem=problem,
            attempts_used=state["attempts_used"],
        )
        if added_to_uncaught and token_service.is_kitten(repository, body.user_id):
            tokens_lost = 1
            token_service.deduct_for_failed_attempt(repository, body.user_id)

    return SubmitResponse(
        passed=passed,
        tests_run=result.get("tests_run", 0),
        tests_passed=result.get("tests_passed", 0),
        failed_test=result.get("failed_test"),
        error_message=result.get("error_message"),
        fishing_reward_granted=granted,
        new_fishing_chances=new_chances,
        attempts_used=state["attempts_used"],
        attempts_remaining=max(0, max_attempts - state["attempts_used"]),
        max_attempts=max_attempts,
        solution_revealed=solution_revealed,
        solution_code=solution_code,
        added_to_uncaught_fish=added_to_uncaught,
        tokens_lost=tokens_lost,
    )


@router.get("/uncaught/{user_id}", response_model=List[UncaughtProblem])
async def list_uncaught(
    user_id: str,
    repository: Repository = Depends(repo),
):
    return [
        UncaughtProblem(**problem)
        for problem in repository.list_uncaught_problems(user_id)
    ]
