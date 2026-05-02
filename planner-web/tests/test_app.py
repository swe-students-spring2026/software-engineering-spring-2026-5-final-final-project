import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("planner_web_app", ROOT / "app.py")
planner_web_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner_web_app)
app = planner_web_app.app
app.template_folder = str(ROOT / "templates")
app.static_folder = str(ROOT / "static")
get_preparation_hours = planner_web_app.get_preparation_hours


def test_auth_page_loads():
    app.config["TESTING"] = True
    response = app.test_client().get("/auth")
    assert response.status_code == 200


def test_study_sessions_requires_login():
    app.config["TESTING"] = True
    response = app.test_client().get("/study-sessions")
    assert response.status_code == 302


def test_preparation_hours():
    assert get_preparation_hours("Light (~1 hr)") == 1
    assert get_preparation_hours("Unknown") == 0
