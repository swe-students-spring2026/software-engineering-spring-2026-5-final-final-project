from unittest.mock import patch, MagicMock


def _mock_response(json_data, status_code=200):
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.status_code = status_code
    return mock


class TestIndexRoute:
    def test_index_returns_200(self, client):
        res = client.get("/")
        assert res.status_code == 200

    def test_index_returns_html(self, client):
        res = client.get("/")
        assert b"NYU" in res.data or b"html" in res.data.lower()


class TestClassesProxy:
    def test_proxies_to_backend(self, client):
        with patch("app.main.requests.get", return_value=_mock_response([])) as mock_get:
            res = client.get("/api/classes?term=1268")
        assert res.status_code == 200
        mock_get.assert_called_once()
        assert "classes" in mock_get.call_args[0][0]

    def test_passes_query_params(self, client):
        with patch("app.main.requests.get", return_value=_mock_response([])) as mock_get:
            client.get("/api/classes?term=1268&q=algorithms")
        called_params = mock_get.call_args[1].get("params", {})
        assert "term" in called_params

    def test_returns_backend_data(self, client):
        courses = [{"title": "Algorithms", "code": "CSCI-UA 310"}]
        with patch("app.main.requests.get", return_value=_mock_response(courses)):
            res = client.get("/api/classes")
        assert res.get_json() == courses

    def test_forwards_error_status(self, client):
        with patch("app.main.requests.get", return_value=_mock_response({"error": "bad"}, 500)):
            res = client.get("/api/classes")
        assert res.status_code == 500


class TestSchoolsProxy:
    def test_proxies_schools(self, client):
        with patch("app.main.requests.get", return_value=_mock_response(["CAS", "Tandon"])):
            res = client.get("/api/schools")
        assert res.status_code == 200
        assert res.get_json() == ["CAS", "Tandon"]


class TestCampusesProxy:
    def test_proxies_campuses(self, client):
        with patch("app.main.requests.get", return_value=_mock_response(["Washington Sq", "Brooklyn"])):
            res = client.get("/api/campuses")
        assert res.status_code == 200


class TestChatProxy:
    def test_proxies_chat_to_backend(self, client):
        with patch("app.main.requests.post", return_value=_mock_response({"reply": "Hello!"})) as mock_post:
            res = client.post("/api/chat", json={"message": "hi"})
        assert res.status_code == 200
        assert res.get_json()["reply"] == "Hello!"
        mock_post.assert_called_once()

    def test_forwards_json_body(self, client):
        with patch("app.main.requests.post", return_value=_mock_response({"reply": "ok"})) as mock_post:
            client.post("/api/chat", json={"message": "find me CS courses"})
        called_json = mock_post.call_args[1].get("json", {})
        assert called_json.get("message") == "find me CS courses"

    def test_forwards_error_from_backend(self, client):
        with patch("app.main.requests.post", return_value=_mock_response({"error": "quota exceeded"}, 500)):
            res = client.post("/api/chat", json={"message": "hi"})
        assert res.status_code == 500
