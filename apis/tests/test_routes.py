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

    def test_get_classes_with_school_filter(self, client, mock_db):
        mock_db.classes.find.return_value = []
        res = client.get("/classes?school=CAS")
        assert res.status_code == 200
        query = mock_db.classes.find.call_args[0][0]
        assert query.get("school") == "CAS"

    def test_get_classes_with_campus_filter(self, client, mock_db):
        mock_db.classes.find.return_value = []
        res = client.get("/classes?campus=Brooklyn")
        assert res.status_code == 200
        query = mock_db.classes.find.call_args[0][0]
        assert query.get("campus_location") == "Brooklyn"

    def test_get_classes_with_component_filter(self, client, mock_db):
        mock_db.classes.find.return_value = []
        res = client.get("/classes?component=Lecture")
        assert res.status_code == 200
        query = mock_db.classes.find.call_args[0][0]
        assert "component" in query

    def test_get_classes_with_mode_filter(self, client, mock_db):
        mock_db.classes.find.return_value = []
        res = client.get("/classes?mode=In-Person")
        assert res.status_code == 200
        query = mock_db.classes.find.call_args[0][0]
        assert "instructional_method" in query


class TestSchoolsRoute:
    def test_get_schools_returns_200(self, client, mock_db):
        mock_db.classes.distinct.return_value = ["CAS", "Tandon", "Stern"]
        res = client.get("/schools")
        assert res.status_code == 200

    def test_get_schools_returns_sorted_list(self, client, mock_db):
        mock_db.classes.distinct.return_value = ["Tandon", "CAS", "Stern"]
        res = client.get("/schools")
        data = res.get_json()
        assert isinstance(data, list)
        assert data == sorted(data)

    def test_get_schools_filters_empty_values(self, client, mock_db):
        mock_db.classes.distinct.return_value = ["CAS", None, "", "Tandon"]
        res = client.get("/schools")
        data = res.get_json()
        assert None not in data
        assert "" not in data


class TestCampusesRoute:
    def test_get_campuses_returns_200(self, client, mock_db):
        mock_db.classes.distinct.return_value = ["Brooklyn", "Manhattan"]
        res = client.get("/campuses")
        assert res.status_code == 200

    def test_get_campuses_returns_sorted_list(self, client, mock_db):
        mock_db.classes.distinct.return_value = ["Manhattan", "Brooklyn"]
        res = client.get("/campuses")
        data = res.get_json()
        assert isinstance(data, list)
        assert data == sorted(data)

    def test_get_campuses_filters_empty_values(self, client, mock_db):
        mock_db.classes.distinct.return_value = ["Brooklyn", None, "Manhattan"]
        res = client.get("/campuses")
        data = res.get_json()
        assert None not in data


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
