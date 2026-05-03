def score_distraction(face_present=True, looking_away=False, phone_visible=False):
    score = 0
    if not face_present:
        score += 60
    if looking_away:
        score += 25
    if phone_visible:
        score += 30
    return min(score, 100)


def classify_distraction(score):
    if score >= 60:
        return "distracted"
    if score >= 25:
        return "at-risk"
    return "focused"
