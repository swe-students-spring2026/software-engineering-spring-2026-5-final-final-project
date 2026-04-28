import pytest
from client import app

# ======================== Flask /analyze endpoint ========================

SAMPLE_FEEDBACK = """
Clear lectures and well-structured course material made the class easy to follow. 
Expectations and grading criteria were communicated upfront and remained consistent. 
Assignments were challenging but aligned with what was taught. 
The professor was responsive during office hours and provided helpful feedback. 
Overall, a fair and effective instructor.
"""

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def test_analyze_valid_feedback(client):
    response = client.post("/analyze", data={"feedback": SAMPLE_FEEDBACK})
    assert response.status_code == 200
    data = response.get_json()
    assert "overall" in data
    assert "themes" in data

def test_analyze_missing_feedback_field(client):
    response = client.post("/analyze", data={})
    assert response.status_code == 400

def test_analyze_empty_feedback(client):
    response = client.post("/analyze", data={"feedback": "   "})
    assert response.status_code == 400

def test_analyze_returns_valid_score(client):
    response = client.post("/analyze", data={"feedback": SAMPLE_FEEDBACK})
    data = response.get_json()
    assert 0 <= data["overall"]["score"] <= 100

def test_analyze_error_message_on_bad_input(client):
    response = client.post("/analyze", data={"feedback": ""})
    data = response.get_json()
    assert "error" in data