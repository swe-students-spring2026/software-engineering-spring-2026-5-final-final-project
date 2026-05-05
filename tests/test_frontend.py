import importlib
from unittest.mock import MagicMock, patch


def load_frontend_module(monkeypatch):
    monkeypatch.setenv("API_URL", "http://localhost:5001")
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-secret")
    module = importlib.import_module("frontend.app")
    return importlib.reload(module)


def create_test_client(monkeypatch):
    frontend_module = load_frontend_module(monkeypatch)
    frontend_module.app.config["TESTING"] = True
    return frontend_module.app.test_client()


def test_dashboard_redirects_when_not_logged_in(monkeypatch):
    client = create_test_client(monkeypatch)
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_friends_redirects_when_not_logged_in(monkeypatch):
    client = create_test_client(monkeypatch)
    response = client.get("/friends")
    assert response.status_code == 302


def test_add_redirects_when_not_logged_in(monkeypatch):
    client = create_test_client(monkeypatch)
    response = client.get("/add")
    assert response.status_code == 302


def test_login_redirects_to_dashboard_on_success(monkeypatch):
    client = create_test_client(monkeypatch)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "1", "username": "alice"}

    with patch("frontend.app.requests.post", return_value=mock_resp):
        response = client.post("/login", data={"username": "alice", "password": "secret"})

    assert response.status_code == 302
    assert "/" in response.headers["Location"]


def test_login_stays_on_login_on_failure(monkeypatch):
    client = create_test_client(monkeypatch)
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.json.return_value = {"error": "invalid credentials"}

    with patch("frontend.app.requests.post", return_value=mock_resp):
        response = client.post("/login", data={"username": "alice", "password": "wrong"})

    assert response.status_code == 302
    assert "login" in response.headers["Location"]