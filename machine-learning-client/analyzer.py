from textblob import TextBlob

# ======================== Theme keyword definitions ========================
THEMES = {
    "Teaching Quality": [
        "teach", "taught", "explains", "explained", "explanation", "lecture",
        "lectures", "instruction", "instructor", "presentation", "presents",
        "clear", "clarity", "confusing", "confused", "engaging", "boring",
        "interesting", "monotone", "passionate", "enthusiasm", "enthusiastic",
        "knowledgeable", "knowledge", "expertise", "expert",
    ],
    "Workload & Assignments": [
        "assignment", "assignments", "homework", "project", "projects",
        "workload", "work load", "deadline", "deadlines", "exam", "exams",
        "test", "tests", "quiz", "quizzes", "overwhelming", "manageable",
        "reasonable", "fair", "unfair", "too much", "too many", "grading",
        "graded", "grades", "grade", "rubric",
    ],
    "Communication & Availability": [
        "office hours", "available", "availability", "responsive", "respond",
        "email", "replied", "reply", "approachable", "approachability",
        "communicate", "communication", "feedback", "feedbacks", "helpful",
        "unhelpful", "support", "supportive", "accessible",
    ],
    "Course Content & Materials": [
        "material", "materials", "content", "curriculum", "syllabus",
        "textbook", "reading", "readings", "slides", "resources", "resource",
        "relevant", "relevance", "outdated", "updated", "practical",
        "real-world", "examples", "example", "topic", "topics", "subject",
        "course", "class",
    ],
    "Fairness & Assessment": [
        "fair", "fairness", "unfair", "bias", "biased", "objective",
        "subjective", "consistent", "inconsistent", "grading", "graded",
        "grade", "grades", "partial credit", "rubric", "expectations",
        "transparent", "transparency", "strict", "lenient",
    ],
    "Overall Experience": [
        "overall", "experience", "semester", "class", "course", "enjoyed",
        "enjoy", "recommend", "recommended", "worth", "learned", "learn",
        "valuable", "valuable", "waste", "best", "worst", "great", "terrible",
        "amazing", "awful", "love", "hate", "liked", "disliked",
    ],
}


# ======================== Sentiment helpers ========================

def polarity_to_label(polarity: float) -> str:
    if polarity >= 0.35:
        return "Very Positive"
    elif polarity >= 0.1:
        return "Positive"
    elif polarity > -0.1:
        return "Neutral"
    elif polarity > -0.35:
        return "Negative"
    else:
        return "Very Negative"


def polarity_to_score(polarity: float) -> float:
    """Map TextBlob polarity [-1, 1] to a 0-100 score."""
    return round((polarity + 1) / 2 * 100, 1)


def split_sentences(text: str) -> list[str]:
    blob = TextBlob(text)
    return [str(s) for s in blob.sentences] # type: ignore


# ======================== Theme analysis ========================

def extract_theme_sentences(sentences: list[str]) -> dict[str, list[str]]:
    """Map each sentence to the themes. A sentence can belong to multiple themes."""
    theme_sentences: dict[str, list[str]] = {theme: [] for theme in THEMES}

    for sentence in sentences:
        lower = sentence.lower()
        for theme, keywords in THEMES.items():
            if any(kw in lower for kw in keywords):
                theme_sentences[theme].append(sentence)

    return theme_sentences


def analyze_theme(theme_name: str, sentences: list[str]) -> dict | None:
    if not sentences:
        return None  # theme not mentioned; caller filters None values

    polarities = []
    subjectivities = []
    for s in sentences:
        blob = TextBlob(s)
        polarities.append(blob.sentiment.polarity)
        subjectivities.append(blob.sentiment.subjectivity)

    avg_polarity = sum(polarities) / len(polarities)
    avg_subjectivity = sum(subjectivities) / len(subjectivities)

    return {
        "theme": theme_name,
        "score": polarity_to_score(avg_polarity),
        "label": polarity_to_label(avg_polarity),
        "polarity": round(avg_polarity, 4),
        "subjectivity": round(avg_subjectivity, 4),
        "sentence_count": len(sentences),
        "sample_sentences": sentences[:3],  # up to 3 representative sentences
    }


# ======================== Top-level analysis ========================

def analyze_feedback(text: str) -> dict:
    sentences = split_sentences(text)
    theme_sentences = extract_theme_sentences(sentences)

    theme_results = []
    for theme_name, s_list in theme_sentences.items():
        result = analyze_theme(theme_name, s_list)
        if result is not None:
            theme_results.append(result)

    theme_results.sort(key=lambda x: x["sentence_count"], reverse=True)

    # Overall based on detected themes only; fallback to raw TextBlob if none found
    if theme_results:
        avg_polarity = sum(t["polarity"] for t in theme_results) / len(theme_results)
        avg_subjectivity = sum(t["subjectivity"] for t in theme_results) / len(theme_results)
    else:
        blob = TextBlob(text)
        avg_polarity = blob.sentiment.polarity
        avg_subjectivity = blob.sentiment.subjectivity

    return {
        "overall": {
            "score": polarity_to_score(avg_polarity),
            "label": polarity_to_label(avg_polarity),
            "polarity": round(avg_polarity, 4),
            "subjectivity": round(avg_subjectivity, 4),
        },
        "themes": theme_results,
        "themes_detected": len(theme_results),
    }

# ======================== Pretty print helper ========================
def print_results(result: dict) -> None:
    o = result["overall"]
    print("=" * 60)
    print("OVERALL SENTIMENT")
    print("=" * 60)
    print(f"  Score       : {o['score']} / 100")
    print(f"  Label       : {o['label']}")
    print(f"  Polarity    : {o['polarity']}")
    print(f"  Subjectivity: {o['subjectivity']}")

    print()
    print("=" * 60)
    print(f"THEMES DETECTED: {result['themes_detected']}")
    print("=" * 60)
    for t in result["themes"]:
        print(f"\n  [{t['label']}] {t['theme']}  —  Score: {t['score']} / 100")
        print(f"    Polarity: {t['polarity']}  |  Sentences matched: {t['sentence_count']}")
        for s in t["sample_sentences"]:
            print(f"    → \"{s.strip()}\"")