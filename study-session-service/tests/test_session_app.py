import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("study_session_app", ROOT / "app.py")
study_session_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study_session_app)
app = study_session_app.app


def test_health():
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_detect():
    response = app.test_client().post("/detect", json={"looking_away": True})
    assert response.status_code == 200
    assert response.get_json()["status"] == "at-risk"
