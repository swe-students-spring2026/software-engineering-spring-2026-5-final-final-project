from unittest.mock import MagicMock, patch

from app.services.professor_ratings import (
    enrich_classes_with_professor_ratings,
    lookup_professor_rating,
    normalize_instructor_name,
)


def test_normalize_instructor_name_reorders_last_first():
    assert normalize_instructor_name("Klukowska, Joanna") == "Joanna Klukowska"


def test_normalize_instructor_name_skips_tba():
    assert normalize_instructor_name("TBA") == ""


def test_enrich_classes_with_professor_ratings_adds_rating():
    courses = [{"instructor": "Joanna Klukowska", "code": "CSCI-UA 102"}]
    rating = {"rating": 3.3, "url": "https://www.ratemyprofessors.com/professor/1852308"}

    with patch("app.services.professor_ratings.lookup_professor_rating", return_value=rating):
        result = enrich_classes_with_professor_ratings(courses)

    assert result[0]["professor_rating"] == rating


def test_lookup_professor_rating_parses_search_results():
    html = """
    <html><body>
      <a href="/professor/1852308">
        QUALITY 3.3 189 ratings Joanna Klukowska Computer Science New York University
        56% would take again 4.1 level of difficulty
      </a>
    </body></html>
    """
    response = MagicMock()
    response.text = html
    response.raise_for_status.return_value = None

    lookup_professor_rating.cache_clear()
    with patch("app.services.professor_ratings.requests.get", return_value=response):
        result = lookup_professor_rating("Klukowska, Joanna")

    assert result == {
        "source": "Rate My Professors",
        "found_name": "Joanna Klukowska",
        "rating": 3.3,
        "rating_count": 189,
        "would_take_again_percent": 56,
        "difficulty": 4.1,
        "url": "https://www.ratemyprofessors.com/professor/1852308",
    }
