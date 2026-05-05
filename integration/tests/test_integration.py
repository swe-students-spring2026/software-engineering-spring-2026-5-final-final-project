"""Tests for the CatCh integration router."""

import importlib.util
import sys
from pathlib import Path

from fastapi.testclient import TestClient

MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "main.py"
SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))
spec = importlib.util.spec_from_file_location("integration_main", MODULE_PATH)
integration_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(integration_main)

client = TestClient(integration_main.app)


def test_health():
    """Health endpoint returns an ok response."""

    response = client.get("/integration/health")
    assert response.status_code == 200
