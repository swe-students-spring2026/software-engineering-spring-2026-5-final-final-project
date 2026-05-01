from __future__ import annotations

import re
from typing import Any


TERM_SEASONS_BY_DIGIT: dict[str, str] = {
    "2": "Winter",
    "4": "Spring",
    "6": "Summer",
    "8": "Fall",
}

TERM_DIGITS_BY_SEASON = {season.lower(): digit for digit, season in TERM_SEASONS_BY_DIGIT.items()}
_TERM_CODE_RE = re.compile(r"^1(\d{2})([2468])$")
_TERM_LABEL_RE = re.compile(r"^(Winter|Spring|Summer|Fall)\s+(\d{4})$", re.I)


def term_code_to_label(term: str) -> str | None:
    match = _TERM_CODE_RE.fullmatch(str(term or "").strip())
    if not match:
        return None
    year_suffix, semester_digit = match.groups()
    return f"{TERM_SEASONS_BY_DIGIT[semester_digit]} {2000 + int(year_suffix)}"


def term_label_to_code(term: str) -> str | None:
    match = _TERM_LABEL_RE.fullmatch(str(term or "").strip())
    if not match:
        return None
    season, year = match.groups()
    digit = TERM_DIGITS_BY_SEASON[season.lower()]
    return f"1{int(year) % 100:02d}{digit}"


def normalize_term_label(term: str) -> str | None:
    match = _TERM_LABEL_RE.fullmatch(str(term or "").strip())
    if not match:
        return None
    season, year = match.groups()
    return f"{season.capitalize()} {year}"


def normalize_term_code(term: str) -> str:
    term_text = str(term or "").strip()
    return term_label_to_code(term_text) or term_text


def albert_term_label(term: str) -> str:
    term_text = str(term or "").strip()
    return term_code_to_label(term_text) or normalize_term_label(term_text) or term_text


def class_term_filter(term: str, source: str) -> dict[str, Any]:
    if source == "bulletin":
        return {"term.code": normalize_term_code(term)}
    return {"term": albert_term_label(term)}


def flexible_term_filter(term: str) -> dict[str, Any]:
    return {"$or": [{"term.code": normalize_term_code(term)}, {"term": albert_term_label(term)}]}
