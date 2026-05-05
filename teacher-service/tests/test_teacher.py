"""Tests for the CatCh teacher-service FastAPI app."""

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "main.py"
spec = importlib.util.spec_from_file_location("teacher_service_main", MODULE_PATH)
teacher_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teacher_main)

client = TestClient(teacher_main.app)


def test_health():
    """Health endpoint returns an ok status."""

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_teacher_rules_exclude_tokens():
    """Teacher rules keep cat users outside the token system."""

    response = client.get("/teacher/rules")
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "cat"
    assert body["token_system_enabled"] is False
