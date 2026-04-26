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
        mock_db.classes.aggregate.return_value = []
        res = client.get("/classes?term=1268")
        assert res.status_code == 200
        match = mock_db.classes.aggregate.call_args[0][0][0]["$match"]
        assert match.get("term.code") == "1268"

    def test_get_classes_with_query_filter(self, client, mock_db):
        mock_db.classes.aggregate.return_value = []
        res = client.get("/classes?q=algorithms")
        assert res.status_code == 200
        match = mock_db.classes.aggregate.call_args[0][0][0]["$match"]
        assert "$or" in match

    def test_get_classes_with_term_and_query(self, client, mock_db):
        mock_db.classes.aggregate.return_value = []
        res = client.get("/classes?term=1268&q=CS")
        assert res.status_code == 200
        match = mock_db.classes.aggregate.call_args[0][0][0]["$match"]
        assert "term.code" in match
        assert "$or" in match

    def test_get_classes_with_school_filter(self, client, mock_db):
        mock_db.classes.aggregate.return_value = []
        res = client.get("/classes?school=CAS")
        assert res.status_code == 200
        match = mock_db.classes.aggregate.call_args[0][0][0]["$match"]
        assert "school" in match

    def test_get_classes_with_campus_filter(self, client, mock_db):
        mock_db.classes.aggregate.return_value = []
        res = client.get("/classes?campus=Brooklyn")
        assert res.status_code == 200
        match = mock_db.classes.aggregate.call_args[0][0][0]["$match"]
        assert "_details_raw.campus_location" in match

    def test_get_classes_with_component_filter(self, client, mock_db):
        mock_db.classes.aggregate.return_value = []
        res = client.get("/classes?component=Lecture")
        assert res.status_code == 200
        match = mock_db.classes.aggregate.call_args[0][0][0]["$match"]
        assert "component" in match

    def test_get_classes_with_mode_filter(self, client, mock_db):
        mock_db.classes.aggregate.return_value = []
        res = client.get("/classes?mode=In-Person")
        assert res.status_code == 200
        match = mock_db.classes.aggregate.call_args[0][0][0]["$match"]
        assert "_details_raw.instructional_method" in match


class TestSchoolsRoute:
    def test_get_schools_returns_200(self, client, mock_db):
        mock_db.classes.distinct.return_value = ["CAS", "Tandon", "Stern"]
        res = client.get("/classes/schools")
        assert res.status_code == 200

    def test_get_schools_returns_sorted_list(self, client, mock_db):
        mock_db.classes.distinct.return_value = ["Tandon", "CAS", "Stern"]
        res = client.get("/classes/schools")
        data = res.get_json()
        assert isinstance(data, list)
        assert data == sorted(data)

    def test_get_schools_filters_empty_values(self, client, mock_db):
        mock_db.classes.distinct.return_value = ["CAS", None, "", "Tandon"]
        res = client.get("/classes/schools")
        data = res.get_json()
        assert None not in data
        assert "" not in data


class TestCampusesRoute:
    def test_get_campuses_returns_200(self, client, mock_db):
        mock_db.classes.distinct.return_value = ["Brooklyn", "Manhattan"]
        res = client.get("/classes/campuses")
        assert res.status_code == 200

    def test_get_campuses_returns_sorted_list(self, client, mock_db):
        mock_db.classes.distinct.return_value = ["Manhattan", "Brooklyn"]
        res = client.get("/classes/campuses")
        data = res.get_json()
        assert isinstance(data, list)
        assert data == sorted(data)

    def test_get_campuses_filters_empty_values(self, client, mock_db):
        mock_db.classes.distinct.return_value = ["Brooklyn", None, "Manhattan"]
        res = client.get("/classes/campuses")
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


class TestAuthRegisterRoute:
    def test_register_rejects_non_nyu_email(self, client):
        res = client.post("/auth/register", json={"email": "user@gmail.com", "password": "password123"})
        assert res.status_code == 400
        assert "nyu.edu" in res.get_json()["error"]

    def test_register_rejects_short_password(self, client):
        res = client.post("/auth/register", json={"email": "user@nyu.edu", "password": "short"})
        assert res.status_code == 400
        assert "8" in res.get_json()["error"]

    def test_register_rejects_duplicate_email(self, client, mock_db):
        mock_db.users.find_one.return_value = {"email": "user@nyu.edu"}
        res = client.post("/auth/register", json={"email": "user@nyu.edu", "password": "password123"})
        assert res.status_code == 409
        assert "error" in res.get_json()

    def test_register_creates_new_user(self, client, mock_db):
        mock_db.users.find_one.return_value = None
        mock_db.users.insert_one.return_value = None
        res = client.post("/auth/register", json={"email": "new@nyu.edu", "password": "password123", "name": "Test"})
        assert res.status_code == 201
        mock_db.users.insert_one.assert_called_once()


class TestAuthLoginRoute:
    def test_login_returns_401_for_unknown_user(self, client, mock_db):
        mock_db.users.find_one.return_value = None
        res = client.post("/auth/login", json={"email": "ghost@nyu.edu", "password": "password123"})
        assert res.status_code == 401

    def test_login_returns_401_for_wrong_password(self, client, mock_db):
        from werkzeug.security import generate_password_hash
        mock_db.users.find_one.return_value = {
            "email": "user@nyu.edu",
            "name": "User",
            "password": generate_password_hash("correctpassword"),
        }
        res = client.post("/auth/login", json={"email": "user@nyu.edu", "password": "wrongpassword"})
        assert res.status_code == 401

    def test_login_returns_200_for_correct_credentials(self, client, mock_db):
        from werkzeug.security import generate_password_hash
        mock_db.users.find_one.return_value = {
            "email": "user@nyu.edu",
            "name": "Test User",
            "password": generate_password_hash("correctpassword"),
        }
        res = client.post("/auth/login", json={"email": "user@nyu.edu", "password": "correctpassword"})
        assert res.status_code == 200
        assert res.get_json()["name"] == "Test User"


class TestAuthGoogleRoute:
    def test_google_rejects_non_nyu_email(self, client):
        res = client.post("/auth/google", json={"email": "user@gmail.com", "name": "Test"})
        assert res.status_code == 400

    def test_google_upserts_nyu_user(self, client, mock_db):
        mock_db.users.update_one.return_value = None
        res = client.post("/auth/google", json={"email": "user@nyu.edu", "name": "Test User"})
        assert res.status_code == 200
        assert res.get_json()["message"] == "ok"
        mock_db.users.update_one.assert_called_once()
