# grader-service

Sandboxed Python code execution. Receives student code + test code, runs them in an isolated subprocess with resource limits and a timeout, returns a structured pass/fail result.

This service is the only place in the system that runs untrusted code. Everything else (game-service, auth-service, mongo) stays clean.

## Status (phase 1)

- [x] FastAPI `/grade` endpoint
- [x] subprocess-based Python execution
- [x] RLIMIT (CPU, memory, processes) on Linux
- [x] Wall-clock timeout
- [x] Per-request nonce in result marker, anti-spoof
- [x] Exit-code + marker double validation
- [x] pytest suite with integration tests
- [ ] Multi-language support (currently Python only)

## Run locally

```bash
cd grader-service
pipenv install --dev

cp .env.example .env
pipenv run uvicorn app.main:app --reload --port 8001
```

Visit http://localhost:8001/docs for interactive API docs.

## Run tests

```bash
pytest --cov=app --cov-report=term-missing
```

The integration tests actually spawn Python subprocesses. They take a few seconds total.

## API

`POST /grade`

Request:
```json
{
  "language": "python",
  "student_code": "def add(a, b):\n    return a + b\n",
  "test_code": "import unittest\n\nclass AddTest(unittest.TestCase):\n    def test_basic(self):\n        self.assertEqual(add(2, 3), 5)\n"
}
```

Response:
```json
{
  "passed": true,
  "tests_run": 1,
  "tests_passed": 1,
  "failed_test": null,
  "error_message": null
}
```

On failure, `failed_test` is the name of the first failing test method, and `error_message` contains the truncated traceback from stderr.

## How grading works

1. A 16-byte hex nonce is generated for this request.
2. We assemble `student_code + test_code + harness`, where `harness` is auto-injected and uses `unittest.TestLoader().loadTestsFromModule(__main__)` to pick up any `unittest.TestCase` defined above.
3. Harness prints exactly one line on success/failure: `GRADER_RESULT_<nonce>:passed:N/M` or `GRADER_RESULT_<nonce>:failed:<name>:N/M`. Then it `sys.exit(0)` or `sys.exit(1)`.
4. We run the script via `subprocess.run([python, "-"], input=script, ...)` with `preexec_fn` setting RLIMITs and a wall-clock timeout.
5. We parse stdout for our nonce-tagged marker. If the exit code disagrees with the marker (`passed=True` but `returncode != 0`), we treat that as a fail.

The nonce is unpredictable to student code (generated at request time, never sent in the request). A student who prints a fake marker with a guessed nonce will not match what we look for.

## Security boundaries

This service handles untrusted code. The defenses below are layered:

**Process isolation (Python `resource` module, Linux only)**
- `RLIMIT_CPU` = 5s of CPU time
- `RLIMIT_AS` = 512 MB virtual memory (catches `'a' * 10**9` bombs)
- `RLIMIT_NPROC` = 64 processes per uid (catches fork bombs)

**Wall-clock timeout**
- Default 10s, configurable via `GRADER_TIMEOUT_SECONDS`. Catches infinite loops that don't burn CPU (e.g., `time.sleep(99999)`).

**Container isolation (in docker-compose)**
- Runs as non-root user `grader` inside the container
- `read_only: true` filesystem
- `tmpfs` for `/tmp` only, capped at 64 MB
- `cap_drop: [ALL]` removes Linux capabilities
- `security_opt: no-new-privileges` blocks setuid escalation
- `pids_limit: 256` at the container level
- Not exposed to the host network; only reachable via the `backend` docker network

**Result anti-spoofing**
- Per-request 128-bit nonce embedded in the result marker
- Exit code + marker double check

## Known limitations (phase 1)

- Container-level isolation only. Container breakouts via kernel exploits are not defended; that would require gVisor or microVM (Firecracker) which is outside this project's scope.
- Student code can read `os.environ` of the grader process. We avoid putting secrets in grader-service env.
- Student code can `import socket` and try to call out. The docker network only contains game-service and grader-service, with no internet egress configured by default. If you add internet egress to this network later, also configure egress filtering or the `network_mode: none` option.
- A sufficiently sophisticated student could `monkeypatch unittest` before the harness runs. The double-validation (exit code + marker) catches naive attempts but not all cases. If this becomes a real problem, switch the harness from importing `unittest` after student code to running tests in a fresh `subprocess` from inside the harness.
- Memory limits applied via RLIMIT can cause Python itself to fail to allocate during interpreter startup on some platforms. Tested on `python:3.12-slim` Docker image, fine there.
