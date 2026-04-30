from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

RMP_BASE_URL = "https://www.ratemyprofessors.com"
RMP_NYU_SCHOOL_ID = "675"
RMP_NYU_FALLBACK_QUERY = "NYU"

_SKIP_INSTRUCTORS = {"", "staff", "tba", "to be announced"}

# Pre-compiled regex patterns
_RE_SPACES = re.compile(r"\s+")
_RE_TITLE_PREFIX = re.compile(r"^(dr|prof|professor)\.?\s+", re.I)
_RE_PARENS = re.compile(r"\s*\([^)]*\)")
_RE_NON_NAME = re.compile(r"[^A-Za-z0-9' -]")
_RE_INSTRUCTOR_SPLIT = re.compile(r"\s*(?:;|/|\||&| and )\s*")
_RE_COMPARE_STRIP = re.compile(r"[^a-z0-9]")
_RE_CLEAN_ID = re.compile(r"[^A-Za-z0-9_-]")

# Persistent HTTP session — reuses TCP/TLS connections across RMP calls
_RMP_SESSION = requests.Session()
_RMP_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
})

# In-memory L1 cache (survives for process lifetime)
_RATING_CACHE: dict[str, dict[str, Any] | None] = {}

# MongoDB L2 cache (survives restarts; 7-day TTL)
_prof_ratings_db = None


def init_professor_ratings(db: Any) -> None:
    global _prof_ratings_db
    _prof_ratings_db = db
    coll = db.professor_ratings_cache
    coll.create_index("_id")
    coll.create_index("scraped_at", expireAfterSeconds=7 * 24 * 3600)


def _rmp_get(url: str) -> requests.Response:
    """Single patchable entry-point for all RMP HTTP calls."""
    return _RMP_SESSION.get(url, timeout=10)


def _collapse_spaces(value: str) -> str:
    return _RE_SPACES.sub(" ", value).strip()


def normalize_instructor_name(raw_name: str) -> str:
    name = _collapse_spaces(raw_name or "")
    if not name:
        return ""

    name = _RE_TITLE_PREFIX.sub("", name)
    name = _RE_PARENS.sub("", name)

    if "," in name:
        last, first = [part.strip() for part in name.split(",", 1)]
        if last and first:
            name = f"{first} {last}"

    name = _RE_NON_NAME.sub(" ", name)
    name = _collapse_spaces(name)
    lowered = name.lower()
    return "" if lowered in _SKIP_INSTRUCTORS else name


def split_instructor_names(raw_name: str) -> list[str]:
    parts = _RE_INSTRUCTOR_SPLIT.split(raw_name or "")
    names: list[str] = []
    seen: set[str] = set()
    for part in parts:
        normalized = normalize_instructor_name(part)
        if not normalized:
            continue
        key = _normalize_compare_key(normalized)
        if not key or key in seen:
            continue
        seen.add(key)
        names.append(normalized)
    return names


def _normalize_compare_key(value: str) -> str:
    return _RE_COMPARE_STRIP.sub("", normalize_instructor_name(value).lower())


def _extract_numeric(pattern: str, text: str, cast):
    match = re.search(pattern, text, flags=re.I)
    if not match:
        return None
    try:
        return cast(match.group(1))
    except (TypeError, ValueError):
        return None


def _build_result(candidate_name: str, href: str, text: str) -> dict[str, Any]:
    rating = _extract_numeric(r"QUALITY\s+([0-9]+(?:\.[0-9]+)?)", text, float)
    rating_count = _extract_numeric(r"([0-9]+)\s+ratings", text, int)
    would_take_again = _extract_numeric(r"([0-9]+)%\s+would take again", text, int)
    difficulty = _extract_numeric(r"([0-9]+(?:\.[0-9]+)?)\s+level of difficulty", text, float)
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
    nyu_index = text.find(" NYU")
    if nyu_index != -1:
        text = text[:nyu_index]
    return _collapse_spaces(text)


def _search_professor_rating(normalized_name: str, url: str) -> dict[str, Any] | None:
    if not normalized_name:
        return None

    try:
        response = _rmp_get(url)
        response.raise_for_status()
    except requests.RequestException:
        return None

    target_key = _normalize_compare_key(normalized_name)
    # lxml is ~3× faster than html.parser; fall back if not installed
    try:
        soup = BeautifulSoup(response.text, "lxml")
    except Exception:
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


def _fetch_from_rmp(normalized_name: str) -> dict[str, Any] | None:
    """Fetch rating from RMP (two-pass: scoped then fallback)."""
    scoped_url = (
        f"{RMP_BASE_URL}/search/professors/{RMP_NYU_SCHOOL_ID}"
        f"?q={quote(normalized_name)}"
    )
    result = _search_professor_rating(normalized_name, scoped_url)
    if result:
        return result

    fallback_query = quote(f"{normalized_name} {RMP_NYU_FALLBACK_QUERY}")
    fallback_url = f"{RMP_BASE_URL}/search/professors?q={fallback_query}"
    return _search_professor_rating(normalized_name, fallback_url)


def lookup_professor_rating(instructor_name: str) -> dict[str, Any] | None:
    """Look up a professor's RMP rating.

    Cache hierarchy: in-memory dict → MongoDB (7-day TTL) → live RMP fetch.
    The lru_cache decorator is NOT used so that we can safely call cache_clear
    from tests without side effects on the MongoDB layer.
    """
    normalized_name = normalize_instructor_name(instructor_name)
    if not normalized_name:
        return None

    cache_key = _normalize_compare_key(normalized_name)
    if not cache_key:
        return None

    # L1: in-memory
    if cache_key in _RATING_CACHE:
        return _RATING_CACHE[cache_key]

    # L2: MongoDB
    if _prof_ratings_db is not None:
        try:
            cached = _prof_ratings_db.professor_ratings_cache.find_one({"_id": cache_key})
            if isinstance(cached, dict):
                result: dict[str, Any] | None = (
                    {k: v for k, v in cached.items() if k not in {"_id", "scraped_at", "has_result"}}
                    if cached.get("has_result")
                    else None
                )
                _RATING_CACHE[cache_key] = result
                return result
        except Exception:
            pass

    # L3: live RMP fetch
    result = _fetch_from_rmp(normalized_name)

    # Persist to MongoDB L2
    if _prof_ratings_db is not None:
        try:
            doc: dict[str, Any] = {
                "_id": cache_key,
                "scraped_at": datetime.now(timezone.utc),
                "has_result": result is not None,
            }
            if result:
                doc.update(result)
            _prof_ratings_db.professor_ratings_cache.update_one(
                {"_id": cache_key}, {"$set": doc}, upsert=True
            )
        except Exception:
            pass

    _RATING_CACHE[cache_key] = result
    return result


def lookup_professor_rating_cache_clear() -> None:
    """Clear the in-memory L1 cache (used by tests)."""
    _RATING_CACHE.clear()


# Keep a .cache_clear attribute so existing call sites (tests) work unchanged
lookup_professor_rating.cache_clear = lookup_professor_rating_cache_clear  # type: ignore[attr-defined]


def enrich_classes_with_professor_ratings(classes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add professor_rating / professor_ratings fields to each course dict.

    Fetches all unique instructor names in parallel (up to 8 threads), then
    reads results from cache to build the enriched list.  Returns new dicts
    (does not mutate the originals).
    """
    # Collect unique instructor names across all courses
    all_names: set[str] = set()
    for course in classes:
        for name in split_instructor_names(course.get("instructor", "")):
            all_names.add(name)

    # Parallel warm-up: fill L1/L2 cache for every name at once
    if all_names:
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(lookup_professor_rating, name): name
                for name in all_names
            }
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass

    # Build enriched list from (now-populated) cache — no additional I/O
    result: list[dict[str, Any]] = []
    for course in classes:
        instructor_names = split_instructor_names(course.get("instructor", ""))
        ratings = [r for name in instructor_names if (r := lookup_professor_rating(name))]
        if ratings:
            enriched = dict(course)
            enriched["professor_rating"] = ratings[0]
            enriched["professor_ratings"] = ratings
            result.append(enriched)
        else:
            result.append(course)
    return result


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


def build_professor_profile(db: Any, name: str, term: str = "") -> dict[str, Any] | None:
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
    ).limit(200))
    if not courses:
        return None

    display_name = next(
        (course.get("instructor", "") for course in courses if course.get("instructor")),
        normalized_name,
    )
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


def search_professors(db: Any, query: str = "", term: str = "", limit: int = 20) -> dict[str, Any]:
    instructor_clause: dict[str, Any] = {"$nin": ["", None]}
    if query:
        instructor_clause = {
            "$nin": ["", None],
            "$regex": re.escape(query),
            "$options": "i",
        }
    mongo_query: dict[str, Any] = {"instructor": instructor_clause}
    if term:
        mongo_query["term.code"] = term

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
