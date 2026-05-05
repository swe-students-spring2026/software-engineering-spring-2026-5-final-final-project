"""Tests for grader-service.

Mix of:
- Pure-function tests for _build_harness, _build_script, _parse_marker (fast, deterministic).
- Integration tests that actually spawn subprocesses through the FastAPI route.
  These require a working Python interpreter on the test host.

Tests set GRADER_TIMEOUT_SECONDS=2 so the timeout test takes 2s instead of 10s.
"""

import os
import subprocess

os.environ["GRADER_TIMEOUT_SECONDS"] = "2"

import pytest
from fastapi.testclient import TestClient

from app.main import (
    app,
    _build_harness,
    _build_script,
    _parse_marker,
    _set_limits,
    grade_python,
)


@pytest.fixture
def client():
    return TestClient(app)


# --- pure-function tests ---


def test_build_harness_embeds_nonce():
    h = _build_harness("abc123")
    assert "GRADER_RESULT_abc123" in h
    # different nonces produce different harnesses
    assert _build_harness("xyz") != h


def test_build_script_contains_all_three_sections():
    s = _build_script("STUDENT", "TEST", "n0")
    assert "STUDENT" in s
    assert "TEST" in s
    assert "GRADER_RESULT_n0" in s
    # student code comes before test code which comes before harness
    assert s.index("STUDENT") < s.index("TEST") < s.index("GRADER_RESULT_n0")


def test_parse_marker_passed():
    out = "some preamble\nGRADER_RESULT_xyz:passed:9/9\n"
    parsed = _parse_marker(out, "xyz")
    assert parsed == {"passed": True, "tests_passed": 9, "tests_run": 9}


def test_parse_marker_failed():
    out = "GRADER_RESULT_xyz:failed:test_thing:3/9\n"
    parsed = _parse_marker(out, "xyz")
    assert parsed == {
        "passed": False,
        "failed_test": "test_thing",
        "tests_passed": 3,
        "tests_run": 9,
    }


def test_parse_marker_wrong_nonce_returns_none():
    out = "GRADER_RESULT_attacker_nonce:passed:99/99\n"
    assert _parse_marker(out, "real_nonce") is None


def test_parse_marker_no_marker_returns_none():
    assert _parse_marker("just regular output\n", "any") is None


def test_parse_marker_takes_last_when_multiple():
    out = "GRADER_RESULT_xyz:failed:test_a:0/1\n" + "GRADER_RESULT_xyz:passed:1/1\n"
    parsed = _parse_marker(out, "xyz")
    assert parsed["passed"] is True


def test_set_limits_ignores_rejected_resource_limits(monkeypatch):
    """Linux resource limit setup ignores unsupported kernel limits."""

    calls = []

    def fake_setrlimit(limit_name, values):
        calls.append((limit_name, values))
        raise OSError("unsupported")

    monkeypatch.setattr("app.main.sys.platform", "linux")
    monkeypatch.setattr("app.main.resource.setrlimit", fake_setrlimit)
    _set_limits()
    assert len(calls) == 3


def test_grade_python_detects_marker_exit_mismatch(monkeypatch):
    """A passing marker with a failing process is treated as failure."""

    completed = subprocess.CompletedProcess(
        args=["python"],
        returncode=1,
        stdout="GRADER_RESULT_nonce:passed:1/1\n",
        stderr="",
    )

    monkeypatch.setattr("app.main.secrets.token_hex", lambda size: "nonce")
    monkeypatch.setattr("app.main.subprocess.run", lambda *args, **kwargs: completed)
    result = grade_python("def x(): pass", "import unittest")
    assert result.passed is False
    assert result.error_message == "grader marker mismatch with exit code"


# --- HTTP route tests ---


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["service"] == "grader-service"


def test_grade_unsupported_language(client):
    r = client.post(
        "/grade",
        json={
            "language": "ruby",
            "student_code": "def foo; end",
            "test_code": "...",
        },
    )
    assert r.status_code == 400


def test_grade_rejects_empty_code(client):
    r = client.post(
        "/grade",
        json={
            "language": "python",
            "student_code": "",
            "test_code": "import unittest",
        },
    )
    assert r.status_code == 422


# --- integration tests (real subprocess) ---


def test_grade_correct_solution_passes(client):
    student = "def add(a, b):\n    return a + b\n"
    test_code = (
        "import unittest\n"
        "\n"
        "class AddTest(unittest.TestCase):\n"
        "    def test_basic(self):\n"
        "        self.assertEqual(add(2, 3), 5)\n"
        "\n"
        "    def test_zero(self):\n"
        "        self.assertEqual(add(0, 0), 0)\n"
    )
    r = client.post(
        "/grade",
        json={
            "language": "python",
            "student_code": student,
            "test_code": test_code,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["passed"] is True
    assert data["tests_run"] == 2
    assert data["tests_passed"] == 2
    assert data["failed_test"] is None


def test_grade_wrong_solution_fails_with_test_name(client):
    student = "def add(a, b):\n    return a - b\n"  # bug
    test_code = (
        "import unittest\n"
        "\n"
        "class AddTest(unittest.TestCase):\n"
        "    def test_basic(self):\n"
        "        self.assertEqual(add(2, 3), 5)\n"
        "\n"
        "    def test_zero(self):\n"
        "        self.assertEqual(add(0, 0), 0)\n"
    )
    r = client.post(
        "/grade",
        json={
            "language": "python",
            "student_code": student,
            "test_code": test_code,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["passed"] is False
    assert data["failed_test"] == "test_basic"
    assert data["tests_run"] == 2
    assert data["tests_passed"] == 1


def test_grade_syntax_error_in_student_code(client):
    r = client.post(
        "/grade",
        json={
            "language": "python",
            "student_code": "def broken(:\n    pass\n",
            "test_code": (
                "import unittest\n"
                "class X(unittest.TestCase):\n"
                "    def test_x(self): pass\n"
            ),
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["passed"] is False
    # Some error info should come back, even if just stderr trace
    assert data["error_message"]


def test_grade_runtime_error_in_student_code(client):
    student = "def add(a, b):\n    raise RuntimeError('boom')\n"
    test_code = (
        "import unittest\n"
        "class AddTest(unittest.TestCase):\n"
        "    def test_basic(self):\n"
        "        self.assertEqual(add(1, 2), 3)\n"
    )
    r = client.post(
        "/grade",
        json={
            "language": "python",
            "student_code": student,
            "test_code": test_code,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["passed"] is False
    # RuntimeError surfaces as an error in unittest, counted as failure
    assert data["tests_run"] == 1


def test_grade_timeout(client):
    """Infinite loop must hit the timeout we set in env."""
    student = "def add(a, b):\n    while True:\n        pass\n"
    test_code = (
        "import unittest\n"
        "class T(unittest.TestCase):\n"
        "    def test_x(self):\n"
        "        add(1, 2)\n"
    )
    r = client.post(
        "/grade",
        json={
            "language": "python",
            "student_code": student,
            "test_code": test_code,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["passed"] is False
    assert "tim" in (data["error_message"] or "").lower()


def test_grade_anti_spoof_fake_marker_does_not_pass(client):
    """Student prints a marker with the wrong nonce. Real harness must override."""
    student = (
        "def add(a, b):\n"
        "    print('GRADER_RESULT_attacker_nonce:passed:99/99')\n"
        "    return a - b\n"  # actually wrong
    )
    test_code = (
        "import unittest\n"
        "class AddTest(unittest.TestCase):\n"
        "    def test_basic(self):\n"
        "        self.assertEqual(add(2, 3), 5)\n"
    )
    r = client.post(
        "/grade",
        json={
            "language": "python",
            "student_code": student,
            "test_code": test_code,
        },
    )
    assert r.status_code == 200
    data = r.json()
    # Real harness ran, real test failed.
    assert data["passed"] is False


def test_grade_student_early_sys_exit_does_not_pass(client):
    """Student does sys.exit(0) before harness runs. No marker → fail."""
    student = "import sys\nsys.exit(0)\ndef add(a, b):\n    return a + b\n"
    test_code = (
        "import unittest\n"
        "class AddTest(unittest.TestCase):\n"
        "    def test_basic(self):\n"
        "        self.assertEqual(add(2, 3), 5)\n"
    )
    r = client.post(
        "/grade",
        json={
            "language": "python",
            "student_code": student,
            "test_code": test_code,
        },
    )
    assert r.status_code == 200
    assert r.json()["passed"] is False


def test_grade_real_leap_year_problem(client):
    """End-to-end with the actual leap_year shape from problems.json."""
    student = (
        "def leap_year(year):\n"
        "    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)\n"
    )
    test_code = (
        "import unittest\n"
        "\n"
        "class LeapTest(unittest.TestCase):\n"
        "    def test_2015(self):\n"
        "        self.assertIs(leap_year(2015), False)\n"
        "    def test_1996(self):\n"
        "        self.assertIs(leap_year(1996), True)\n"
        "    def test_2000(self):\n"
        "        self.assertIs(leap_year(2000), True)\n"
        "    def test_1900(self):\n"
        "        self.assertIs(leap_year(1900), False)\n"
    )
    r = client.post(
        "/grade",
        json={
            "language": "python",
            "student_code": student,
            "test_code": test_code,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["passed"] is True
    assert data["tests_run"] == 4
    assert data["tests_passed"] == 4
