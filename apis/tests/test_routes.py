import json
from unittest.mock import patch, MagicMock


class TestHealthRoute:
    def test_health_returns_200(self, client):
        res = client.get("/health")
        assert res.status_code == 200

    def test_health_returns_correct_body(self, client):
        res = client.get("/health")
        data = res.get_json()
        assert data["status"] == "ok"
        assert data["service"] == "apis"


class TestClassesRoute:
    def test_get_classes_returns_200(self, client, mock_db):
        mock_db.classes.find.return_value = []
        res = client.get("/classes")
        assert res.status_code == 200

    def test_get_classes_returns_list(self, client, mock_db):
        mock_db.classes.find.return_value = [
            {"title": "Algorithms", "code": "CSCI-UA 310"}
        ]
        res = client.get("/classes")
        data = res.get_json()
        assert isinstance(data, list)

    def test_get_classes_with_term_filter(self, client, mock_db):
        mock_db.classes.find.return_value = []
        res = client.get("/classes?term=1268")
        assert res.status_code == 200
        call_args = mock_db.classes.find.call_args
        assert call_args[0][0].get("term.code") == "1268"

    def test_get_classes_with_query_filter(self, client, mock_db):
        mock_db.classes.find.return_value = []
        res = client.get("/classes?q=algorithms")
        assert res.status_code == 200
        call_args = mock_db.classes.find.call_args
        assert "$or" in call_args[0][0]

    def test_get_classes_with_term_and_query(self, client, mock_db):
        mock_db.classes.find.return_value = []
        res = client.get("/classes?term=1268&q=CS")
        assert res.status_code == 200
        query = mock_db.classes.find.call_args[0][0]
        assert "term.code" in query
        assert "$or" in query


class TestRefreshRoute:
    def test_refresh_returns_503_when_scraper_unavailable(self, client):
        # refresh_course_document is None in test env (scrapers not installed)
        from app import main as main_module
        original = main_module.refresh_course_document
        main_module.refresh_course_document = None
        try:
            res = client.post("/classes/refresh", json={})
            assert res.status_code == 503
            assert "error" in res.get_json()
        finally:
            main_module.refresh_course_document = original


class TestProgramsRoute:
    def test_get_programs_returns_200(self, client, mock_db):
        mock_db["program_requirements"].find.return_value.sort.return_value = []
        res = client.get("/programs")
        assert res.status_code == 200

    def test_get_programs_returns_list(self, client, mock_db):
        mock_db["program_requirements"].find.return_value.sort.return_value = [
            {"title": "Computer Science", "url": "/cs"}
        ]
        res = client.get("/programs")
        assert isinstance(res.get_json(), list)


class TestProgramRequirementsRoute:
    def test_missing_url_param_returns_400(self, client):
        res = client.get("/program-requirements")
        assert res.status_code == 400
        assert "error" in res.get_json()

    def test_program_found_returns_200(self, client, mock_db):
        mock_db["program_requirements"].find_one.return_value = {
            "title": "CS", "url": "/cs"
        }
        res = client.get("/program-requirements?url=/cs")
        assert res.status_code == 200

    def test_program_not_found_returns_404(self, client, mock_db):
        mock_db["program_requirements"].find_one.return_value = None
        res = client.get("/program-requirements?url=/nonexistent")
        assert res.status_code == 404
