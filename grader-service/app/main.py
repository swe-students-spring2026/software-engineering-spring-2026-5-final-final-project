"""grader-service: sandboxed Python code execution.

Receives student code + test code, assembles them into a runnable script,
executes it in a subprocess with resource limits and a timeout, and returns
a structured pass/fail verdict.

Anti-spoof: a per-request nonce is embedded in the result marker so student
code cannot forge a PASS by printing a fake marker.
"""

import asyncio
import os
import re
import resource
import secrets
import subprocess
import sys
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# --- limits ---
# RLIMIT_CPU: child process CPU-seconds before SIGKILL
# RLIMIT_AS:  virtual-address-space cap (catches `'a' * 10**9` bombs)
# RLIMIT_NPROC: process count per uid (catches fork bombs)
MAX_CPU_SECONDS = 5
MAX_MEMORY_BYTES = 512 * 1024 * 1024
MAX_PROCESSES = 64


def _wall_clock_timeout() -> float:
    """Read fresh each call so tests can override via env."""
    return float(os.environ.get("GRADER_TIMEOUT_SECONDS", "10"))


# --- models ---


class GradeRequest(BaseModel):
    language: str = Field(default="python")
    student_code: str = Field(..., min_length=1, max_length=20_000)
    test_code: str = Field(..., min_length=1, max_length=20_000)


class GradeResponse(BaseModel):
    passed: bool
    tests_run: int
    tests_passed: int
    failed_test: Optional[str] = None
    error_message: Optional[str] = None


# --- harness ---


def _build_harness(nonce: str) -> str:
    """Test runner appended after student + test code.

    Outputs exactly one line: GRADER_RESULT_<nonce>:passed:N/M  or  :failed:<name>:N/M
    """
    return f"""
# === harness (auto-injected) ===
import unittest as _u
import sys as _sys
import io as _io

_sys.argv = [_sys.argv[0]]

_loader = _u.TestLoader()
_suite = _loader.loadTestsFromModule(_sys.modules['__main__'])

_buf = _io.StringIO()
_runner = _u.TextTestRunner(stream=_buf, verbosity=0)
_result = _runner.run(_suite)

_total = _result.testsRun
_fails = _result.failures + _result.errors

if not _fails:
    print("GRADER_RESULT_{nonce}:passed:" + str(_total) + "/" + str(_total))
    _sys.exit(0)
else:
    _first = _fails[0][0]
    _name = _first._testMethodName if hasattr(_first, "_testMethodName") else "unknown"
    _passed = _total - len(_fails)
    print("GRADER_RESULT_{nonce}:failed:" + _name + ":" + str(_passed) + "/" + str(_total))
    _sys.exit(1)
"""


def _build_script(student_code: str, test_code: str, nonce: str) -> str:
    return f"{student_code}\n\n{test_code}\n\n{_build_harness(nonce)}\n"


# --- subprocess ---


def _set_limits():
    """preexec_fn applied in child before exec. Linux only.

    Each setrlimit call is wrapped because some kernels/configs reject some limits.
    """
    if sys.platform != "linux":
        return
    for setter in (
        lambda: resource.setrlimit(
            resource.RLIMIT_CPU, (MAX_CPU_SECONDS, MAX_CPU_SECONDS)
        ),
        lambda: resource.setrlimit(
            resource.RLIMIT_AS, (MAX_MEMORY_BYTES, MAX_MEMORY_BYTES)
        ),
        lambda: resource.setrlimit(
            resource.RLIMIT_NPROC, (MAX_PROCESSES, MAX_PROCESSES)
        ),
    ):
        try:
            setter()
        except (ValueError, OSError):
            pass


def _parse_marker(stdout: str, nonce: str) -> Optional[dict]:
    """Walk stdout from end to find our marker. Foreign markers without our nonce are ignored."""
    prefix = f"GRADER_RESULT_{nonce}:"
    for line in reversed(stdout.splitlines()):
        if not line.startswith(prefix):
            continue
        payload = line[len(prefix) :]
        if payload.startswith("passed:"):
            m = re.match(r"passed:(\d+)/(\d+)", payload)
            if m:
                return {
                    "passed": True,
                    "tests_passed": int(m.group(1)),
                    "tests_run": int(m.group(2)),
                }
        elif payload.startswith("failed:"):
            m = re.match(r"failed:([^:]+):(\d+)/(\d+)", payload)
            if m:
                return {
                    "passed": False,
                    "failed_test": m.group(1),
                    "tests_passed": int(m.group(2)),
                    "tests_run": int(m.group(3)),
                }
    return None


def grade_python(student_code: str, test_code: str) -> GradeResponse:
    """Grade Python code in the local sandbox."""

    nonce = secrets.token_hex(16)
    script = _build_script(student_code, test_code, nonce)
    preexec = _set_limits if sys.platform == "linux" else None

    try:
        completed = subprocess.run(
            [sys.executable, "-"],
            input=script,
            capture_output=True,
            text=True,
            timeout=_wall_clock_timeout(),
            preexec_fn=preexec,
        )
    except subprocess.TimeoutExpired:
        return GradeResponse(
            passed=False,
            tests_run=0,
            tests_passed=0,
            error_message=f"timed out after {_wall_clock_timeout()}s (likely infinite loop)",
        )

    parsed = _parse_marker(completed.stdout, nonce)

    if parsed is None:
        # Script crashed before reaching the harness (syntax error, sys.exit, etc).
        err = completed.stderr.strip()[-500:] or "code did not produce a grading result"
        return GradeResponse(
            passed=False,
            tests_run=0,
            tests_passed=0,
            error_message=err,
        )

    # Marker says PASS but exit code disagrees: treat as fail (paranoid double-check).
    if parsed["passed"] and completed.returncode != 0:
        return GradeResponse(
            passed=False,
            tests_run=parsed["tests_run"],
            tests_passed=parsed["tests_passed"],
            error_message="grader marker mismatch with exit code",
        )

    return GradeResponse(
        passed=parsed["passed"],
        tests_run=parsed["tests_run"],
        tests_passed=parsed["tests_passed"],
        failed_test=parsed.get("failed_test"),
        error_message=(
            None if parsed["passed"] else (completed.stderr.strip()[-500:] or None)
        ),
    )


# --- app ---

app = FastAPI(
    title="Grader Service",
    description="Sandboxed Python code execution for student submissions",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": "grader-service"}


@app.post("/grade", response_model=GradeResponse, tags=["grade"])
async def grade(body: GradeRequest):
    if body.language != "python":
        raise HTTPException(
            status_code=400,
            detail=f"language '{body.language}' not supported (phase 1: python only)",
        )
    # Run blocking subprocess off the event loop so we don't stall other requests.
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        grade_python,
        body.student_code,
        body.test_code,
    )
