import pytest
from unittest.mock import MagicMock
from app.services.requirements_service import RequirementsService


class TestListUndergraduatePrograms:
    def test_returns_list(self):
        db = MagicMock()
        db["program_requirements"].find.return_value.sort.return_value = [
            {"title": "CS", "url": "/cs"},
            {"title": "Math", "url": "/math"},
        ]
        svc = RequirementsService(db)
        result = svc.list_undergraduate_programs()
        assert isinstance(result, list)
        assert len(result) == 2

    def test_returns_empty_list_when_no_programs(self):
        db = MagicMock()
        db["program_requirements"].find.return_value.sort.return_value = []
        svc = RequirementsService(db)
        result = svc.list_undergraduate_programs()
        assert result == []

    def test_calls_correct_collection(self):
        db = MagicMock()
        db["program_requirements"].find.return_value.sort.return_value = []
        svc = RequirementsService(db)
        svc.list_undergraduate_programs()
        db["program_requirements"].find.assert_called_once()


class TestFetchProgramRequirements:
    def test_returns_program_when_found(self):
        db = MagicMock()
        db["program_requirements"].find_one.return_value = {"title": "CS", "url": "/cs"}
        svc = RequirementsService(db)
        result = svc.fetch_program_requirements("/cs")
        assert result["title"] == "CS"

    def test_returns_empty_dict_when_not_found(self):
        db = MagicMock()
        db["program_requirements"].find_one.return_value = None
        svc = RequirementsService(db)
        result = svc.fetch_program_requirements("/nonexistent")
        assert result == {}

    def test_queries_by_url(self):
        db = MagicMock()
        db["program_requirements"].find_one.return_value = None
        svc = RequirementsService(db)
        svc.fetch_program_requirements("/test-url")
        db["program_requirements"].find_one.assert_called_once_with(
            {"url": "/test-url"}, {"_id": 0}
        )
