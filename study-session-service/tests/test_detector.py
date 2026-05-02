from detector import classify_distraction, score_distraction


def test_focus_score_defaults_to_focused():
    assert score_distraction() == 0
    assert classify_distraction(0) == "focused"


def test_missing_face_is_distracted():
    score = score_distraction(face_present=False)
    assert score == 60
    assert classify_distraction(score) == "distracted"
