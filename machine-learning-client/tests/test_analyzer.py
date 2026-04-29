import pytest
from analyzer import (
    polarity_to_label,
    polarity_to_score,
    split_sentences,
    extract_theme_sentences,
    analyze_theme,
    analyze_feedback,
    print_results,
)

# ======================== polarity_to_label ========================

def test_polarity_to_label_very_positive():
    assert polarity_to_label(1.0) == "Very Positive"
    assert polarity_to_label(0.35) == "Very Positive"

def test_polarity_to_label_positive():
    assert polarity_to_label(0.2) == "Positive"
    assert polarity_to_label(0.1) == "Positive"

def test_polarity_to_label_neutral():
    assert polarity_to_label(0.0) == "Neutral"
    assert polarity_to_label(0.09) == "Neutral"
    assert polarity_to_label(-0.09) == "Neutral"

def test_polarity_to_label_negative():
    assert polarity_to_label(-0.2) == "Negative"
    assert polarity_to_label(-0.1) == "Negative"

def test_polarity_to_label_very_negative():
    assert polarity_to_label(-1.0) == "Very Negative"
    assert polarity_to_label(-0.35) == "Very Negative"


# ======================== polarity_to_score ========================

def test_polarity_to_score_max():
    assert polarity_to_score(1.0) == 100.0

def test_polarity_to_score_min():
    assert polarity_to_score(-1.0) == 0.0

def test_polarity_to_score_neutral():
    assert polarity_to_score(0.0) == 50.0

def test_polarity_to_score_range():
    score = polarity_to_score(0.5)
    assert 0 <= score <= 100


# ======================== split_sentences ========================

def test_split_sentences_basic():
    text = "The professor is great. The course was hard."
    sentences = split_sentences(text)
    assert len(sentences) == 2

def test_split_sentences_single():
    text = "Great professor."
    sentences = split_sentences(text)
    assert len(sentences) == 1

def test_split_sentences_returns_strings():
    sentences = split_sentences("Good class. Bad exam.")
    assert all(isinstance(s, str) for s in sentences)


# ======================== extract_theme_sentences ========================

def test_extract_theme_sentences_teaching():
    sentences = ["The professor explains things clearly."]
    result = extract_theme_sentences(sentences)
    assert sentences[0] in result["Teaching Quality"]

def test_extract_theme_sentences_workload():
    sentences = ["The exam was overwhelming and unfair."]
    result = extract_theme_sentences(sentences)
    assert sentences[0] in result["Workload & Assignments"]

def test_extract_theme_sentences_no_match():
    sentences = ["The weather outside is nice today."]
    result = extract_theme_sentences(sentences)
    assert all(len(v) == 0 for v in result.values())

def test_extract_theme_sentences_multi_theme():
    # "course" hits Course Content and Overall Experience
    sentences = ["The course materials were excellent."]
    result = extract_theme_sentences(sentences)
    matched_themes = [t for t, s in result.items() if sentences[0] in s]
    assert len(matched_themes) >= 2

def test_extract_theme_sentences_all_themes_present():
    result = extract_theme_sentences([])
    assert set(result.keys()) == {
        "Teaching Quality",
        "Workload & Assignments",
        "Communication & Availability",
        "Course Content & Materials",
        "Fairness & Assessment",
        "Overall Experience",
    }


# ======================== analyze_theme ========================

def test_analyze_theme_returns_none_on_empty():
    assert analyze_theme("Teaching Quality", []) is None

def test_analyze_theme_structure():
    result = analyze_theme("Teaching Quality", ["The professor is very knowledgeable and engaging."])
    assert result is not None
    assert "theme" in result
    assert "score" in result
    assert "label" in result
    assert "polarity" in result
    assert "subjectivity" in result
    assert "sentence_count" in result
    assert "sample_sentences" in result

def test_analyze_theme_score_range():
    result = analyze_theme("Teaching Quality", ["Great instructor who explains things well."])
    assert 0 <= result["score"] <= 100

def test_analyze_theme_sentence_count():
    sentences = ["Good lecture.", "Clear explanation.", "Very engaging."]
    result = analyze_theme("Teaching Quality", sentences)
    assert result["sentence_count"] == 3

def test_analyze_theme_positive_sentiment():
    result = analyze_theme("Teaching Quality", ["The professor is amazing and incredibly helpful."])
    assert result["label"] in ("Positive", "Very Positive")

def test_analyze_theme_negative_sentiment():
    result = analyze_theme("Workload & Assignments", ["The exams were unfair and overwhelming."])
    assert result["label"] in ("Neutral", "Negative", "Very Negative")


# ======================== analyze_feedback ========================

SAMPLE_FEEDBACK = """
Clear lectures and well-structured course material made the class easy to follow. 
Expectations and grading criteria were communicated upfront and remained consistent. 
Assignments were challenging but aligned with what was taught. 
The professor was responsive during office hours and provided helpful feedback. 
Overall, a fair and effective instructor.
"""

def test_analyze_feedback_structure():
    result = analyze_feedback(SAMPLE_FEEDBACK)
    assert "overall" in result
    assert "themes" in result
    assert "themes_detected" in result

    o = result["overall"]
    assert "score" in o
    assert "label" in o
    assert "polarity" in o
    assert "subjectivity" in o

def test_analyze_feedback_overall_score_range():
    result = analyze_feedback(SAMPLE_FEEDBACK)
    assert 0 <= result["overall"]["score"] <= 100

def test_analyze_feedback_themes_detected():
    result = analyze_feedback(SAMPLE_FEEDBACK)
    assert result["themes_detected"] > 0
    assert result["themes_detected"] == len(result["themes"])

def test_analyze_feedback_overall_derived_from_themes():
    result = analyze_feedback(SAMPLE_FEEDBACK)
    themes = result["themes"]
    expected_polarity = round(sum(t["polarity"] for t in themes) / len(themes), 4)
    assert result["overall"]["polarity"] == expected_polarity

def test_analyze_feedback_empty_text_fallback():
    # No themes will match; should fall back to raw TextBlob
    result = analyze_feedback("The sky is blue today.")
    assert "overall" in result
    assert result["themes_detected"] == 0

def test_analyze_feedback_label_is_valid():
    result = analyze_feedback(SAMPLE_FEEDBACK)
    valid_labels = {"Very Positive", "Positive", "Neutral", "Negative", "Very Negative"}
    assert result["overall"]["label"] in valid_labels
    for t in result["themes"]:
        assert t["label"] in valid_labels


# ======================== print_results ========================

def test_print_results_runs_without_error(capsys):
    result = analyze_feedback(SAMPLE_FEEDBACK)
    print_results(result)
    captured = capsys.readouterr()
    assert "OVERALL SENTIMENT" in captured.out
    assert "THEMES DETECTED" in captured.out

def test_print_results_shows_score(capsys):
    result = analyze_feedback(SAMPLE_FEEDBACK)
    print_results(result)
    captured = capsys.readouterr()
    assert "Score" in captured.out

def test_print_results_shows_each_theme(capsys):
    result = analyze_feedback(SAMPLE_FEEDBACK)
    print_results(result)
    captured = capsys.readouterr()
    for t in result["themes"]:
        assert t["theme"] in captured.out