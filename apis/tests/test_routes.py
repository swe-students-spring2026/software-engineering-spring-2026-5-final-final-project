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
        query = mock_db.classes.find.call_args[0][0]
        assert query.get("term") == "Fall 2026"

    def test_get_classes_with_query_filter(self, client, mock_db):
        mock_db.classes.find.return_value = []
        res = client.get("/classes?q=algorithms")
        assert res.status_code == 200
        query = mock_db.classes.find.call_args[0][0]
        assert "$or" in query

    def test_get_classes_with_term_and_query(self, client, mock_db):
        mock_db.classes.find.return_value = []
        res = client.get("/classes?term=1268&q=CS")
        assert res.status_code == 200
        query = mock_db.classes.find.call_args[0][0]
        assert query.get("term") == "Fall 2026"
        assert "$or" in query

    def test_get_classes_with_school_filter(self, client, mock_db):
        mock_db.classes.find.return_value = []
        res = client.get("/classes?school=CAS")
        assert res.status_code == 200
        query = mock_db.classes.find.call_args[0][0]
        assert "school" in query

    def test_get_classes_with_component_filter(self, client, mock_db):
        mock_db.classes.find.return_value = []
        res = client.get("/classes?component=Lecture")
        assert res.status_code == 200
        query = mock_db.classes.find.call_args[0][0]
        assert "component" in query

    def test_get_classes_with_status_open_filter(self, client, mock_db):
        mock_db.classes.find.return_value = []
        res = client.get("/classes?status=open")
        assert res.status_code == 200
        query = mock_db.classes.find.call_args[0][0]
        assert "status" in query

    def test_get_classes_with_status_waitlist_filter(self, client, mock_db):
        mock_db.classes.find.return_value = []
        res = client.get("/classes?status=waitlist")
        assert res.status_code == 200
        query = mock_db.classes.find.call_args[0][0]
        assert query["status"]["$regex"].startswith("^wait")

    def test_get_classes_instructor_flexible_match(self, client, mock_db):
        mock_db.classes.find.return_value = []
        res = client.get("/classes?q=Spathis+Promethee")
        assert res.status_code == 200
        query = mock_db.classes.find.call_args[0][0]
        instructor_regex = next(c["instructor"]["$regex"] for c in query["$or"] if "instructor" in c)
        assert ".*" in instructor_regex


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
        res = client.get("/classes/campuses")
        assert res.status_code == 200

    def test_get_campuses_returns_empty_list(self, client, mock_db):
        res = client.get("/classes/campuses")
        assert res.get_json() == []



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


class TestUserProfileRoute:
    def test_get_profile_missing_email_returns_400(self, client):
        res = client.get("/user/profile")
        assert res.status_code == 400
        assert "error" in res.get_json()

    def test_get_profile_not_found_returns_404(self, client, mock_db):
        mock_db.users.find_one.return_value = None
        res = client.get("/user/profile?email=ghost@nyu.edu")
        assert res.status_code == 404

    def test_get_profile_found_returns_200(self, client, mock_db):
        mock_db.users.find_one.return_value = {"email": "user@nyu.edu", "name": "Test", "major": "CS"}
        res = client.get("/user/profile?email=user@nyu.edu")
        assert res.status_code == 200
        assert res.get_json()["major"] == "CS"


class TestUpdateProfileRoute:
    def test_update_missing_email_returns_400(self, client):
        res = client.put("/user/profile", json={"major": "CS"})
        assert res.status_code == 400

    def test_update_no_valid_fields_returns_400(self, client):
        res = client.put("/user/profile", json={"email": "user@nyu.edu", "unknown_field": "x"})
        assert res.status_code == 400

    def test_update_valid_fields_returns_200(self, client, mock_db):
        mock_db.users.update_one.return_value = None
        res = client.put("/user/profile", json={"email": "user@nyu.edu", "major": "CS", "graduation_year": "2026"})
        assert res.status_code == 200
        assert res.get_json()["message"] == "profile updated"
        mock_db.users.update_one.assert_called()


class TestUploadTranscriptRoute:
    def test_missing_email_returns_400(self, client):
        from io import BytesIO
        res = client.post(
            "/user/transcript",
            data={"transcript": (BytesIO(b"%PDF-1.4"), "t.pdf", "application/pdf")},
            content_type="multipart/form-data",
        )
        assert res.status_code == 400

    def test_missing_file_returns_400(self, client):
        res = client.post("/user/transcript", data={"email": "user@nyu.edu"}, content_type="multipart/form-data")
        assert res.status_code == 400

    def test_non_pdf_returns_400(self, client):
        from io import BytesIO
        res = client.post(
            "/user/transcript",
            data={"email": "user@nyu.edu", "transcript": (BytesIO(b"text"), "file.txt", "text/plain")},
            content_type="multipart/form-data",
        )
        assert res.status_code == 400

    def test_valid_pdf_parses_and_saves_courses(self, client, mock_db):
        from io import BytesIO
        from unittest.mock import patch, MagicMock
        mock_db.users.update_one.return_value = None
        fake_page = MagicMock()
        fake_page.extract_text.return_value = "CSCI-UA 101 Intro to CS A\nMATH-UA 123 Calculus B"
        fake_reader = MagicMock()
        fake_reader.pages = [fake_page]
        with patch("pypdf.PdfReader", return_value=fake_reader):
            with patch("app.ai.service.parse_transcript", return_value=["CSCI-UA 101", "MATH-UA 123"]):
                res = client.post(
                    "/user/transcript",
                    data={"email": "user@nyu.edu", "transcript": (BytesIO(b"%PDF-1.4"), "t.pdf", "application/pdf")},
                    content_type="multipart/form-data",
                )
        assert res.status_code == 200
        data = res.get_json()
        assert data["count"] == 2
