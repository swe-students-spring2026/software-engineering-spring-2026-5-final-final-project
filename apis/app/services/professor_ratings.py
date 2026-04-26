from __future__ import annotations

import re
from functools import lru_cache
from typing import Any
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

RMP_BASE_URL = "https://www.ratemyprofessors.com"
RMP_NYU_SCHOOL_ID = "675"
RMP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

_SKIP_INSTRUCTORS = {"", "staff", "tba", "to be announced"}


def _collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_instructor_name(raw_name: str) -> str:
    name = _collapse_spaces(raw_name or "")
    if not name:
        return ""

    name = re.split(r"\s*(?:;|/|\||&| and )\s*", name, maxsplit=1)[0]
    name = re.sub(r"^(dr|prof|professor)\.?\s+", "", name, flags=re.I)
    name = re.sub(r"\s*\([^)]*\)", "", name)

    if "," in name:
        last, first = [part.strip() for part in name.split(",", 1)]
        if last and first:
            name = f"{first} {last}"

    name = re.sub(r"[^A-Za-z0-9' -]", " ", name)
    name = _collapse_spaces(name)
    lowered = name.lower()
    return "" if lowered in _SKIP_INSTRUCTORS else name


def _normalize_compare_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", normalize_instructor_name(value).lower())


def _extract_numeric(pattern: str, text: str, cast):
    match = re.search(pattern, text, flags=re.I)
    if not match:
        return None
    try:
        return cast(match.group(1))
    except (TypeError, ValueError):
        return None


def _build_result(candidate_name: str, href: str, text: str) -> dict[str, Any]:
    rating = _extract_numeric(r"QUALITY\s+([0-9]+(?:\.[0-9])?)", text, float)
    rating_count = _extract_numeric(r"([0-9]+)\s+ratings", text, int)
    would_take_again = _extract_numeric(r"([0-9]+)%\s+would take again", text, int)
    difficulty = _extract_numeric(r"([0-9]+(?:\.[0-9])?)\s+level of difficulty", text, float)
    if rating is None or rating_count is None:
        return {}

    return {
        "source": "Rate My Professors",
        "found_name": candidate_name,
        "rating": rating,
        "rating_count": rating_count,
        "would_take_again_percent": would_take_again,
        "difficulty": difficulty,
        "url": f"{RMP_BASE_URL}{href}",
    }


def _candidate_prefix(text: str) -> str:
    if " ratings " in text:
        text = text.split(" ratings ", 1)[1]
    school_index = text.find(" New York University")
    if school_index != -1:
        text = text[:school_index]
    return _collapse_spaces(text)


@lru_cache(maxsize=4096)
def lookup_professor_rating(instructor_name: str) -> dict[str, Any] | None:
    normalized_name = normalize_instructor_name(instructor_name)
    if not normalized_name:
        return None

    url = f"{RMP_BASE_URL}/search/professors/{RMP_NYU_SCHOOL_ID}?q={quote(normalized_name)}"
    try:
        response = requests.get(url, headers=RMP_HEADERS, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return None

    target_key = _normalize_compare_key(normalized_name)
    soup = BeautifulSoup(response.text, "html.parser")

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        if not href.startswith("/professor/"):
            continue

        text = _collapse_spaces(anchor.get_text(" ", strip=True))
        prefix = _candidate_prefix(text)
        candidate_words = prefix.split()
        target_words = normalized_name.split()
        candidate_name = " ".join(candidate_words[: len(target_words)])
        if _normalize_compare_key(candidate_name) != target_key:
            continue

        result = _build_result(candidate_name, href, text)
        return result or None

    return None


def enrich_classes_with_professor_ratings(classes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for course in classes:
        instructor = course.get("instructor", "")
        rating = lookup_professor_rating(instructor)
        if rating:
            course["professor_rating"] = rating
    return classes


def instructor_regex(name: str) -> str:
    normalized = normalize_instructor_name(name)
    if not normalized:
        return ""
    tokens = normalized.split()
    if len(tokens) < 2:
        return re.escape(normalized)
    first = re.escape(tokens[0])
    last = re.escape(tokens[-1])
    return rf"(?:{first}.*{last}|{last},?\s*{first})"


def build_professor_profile(db, name: str, term: str = "") -> dict[str, Any] | None:
    normalized_name = normalize_instructor_name(name)
    if not normalized_name:
        return None

    query: dict[str, Any] = {
        "instructor": {"$regex": instructor_regex(normalized_name), "$options": "i"}
    }
    if term:
        query["term.code"] = term

    courses = list(db.classes.find(
        query,
        {
            "_id": 0,
            "code": 1,
            "title": 1,
            "section": 1,
            "crn": 1,
            "component": 1,
            "term": 1,
            "status": 1,
            "meets_human": 1,
            "meeting_times": 1,
            "school": 1,
            "instructor": 1,
        },
    ))
    if not courses:
        return None

    display_name = next((course.get("instructor", "") for course in courses if course.get("instructor")), normalized_name)
    rating = lookup_professor_rating(display_name)

    courses.sort(key=lambda course: (
        course.get("code", ""),
        course.get("section", ""),
        course.get("component", ""),
    ))

    unique_codes: list[str] = []
    seen_codes: set[str] = set()
    for course in courses:
        code = course.get("code", "")
        if code and code not in seen_codes:
            seen_codes.add(code)
            unique_codes.append(code)

    return {
        "name": display_name,
        "normalized_name": normalized_name,
        "professor_rating": rating,
        "courses": courses,
        "course_codes": unique_codes,
        "course_count": len(courses),
    }


def search_professors(db, query: str = "", term: str = "", limit: int = 20) -> dict[str, Any]:
    mongo_query: dict[str, Any] = {"instructor": {"$nin": ["", None]}}
    if term:
        mongo_query["term.code"] = term
    if query:
        mongo_query["instructor"] = {"$regex": re.escape(query), "$options": "i"}

    pipeline = [
        {"$match": mongo_query},
        {"$group": {
            "_id": "$instructor",
            "course_codes": {"$addToSet": "$code"},
            "section_count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
        {"$limit": limit},
    ]

    results = []
    for row in db.classes.aggregate(pipeline):
        name = row.get("_id", "")
        if not normalize_instructor_name(name):
            continue
        rating = lookup_professor_rating(name)
        results.append({
            "name": name,
            "normalized_name": normalize_instructor_name(name),
            "course_codes": sorted(c for c in row.get("course_codes", []) if c),
            "section_count": row.get("section_count", 0),
            "professor_rating": rating,
        })

    return {"professors": results, "count": len(results)}
