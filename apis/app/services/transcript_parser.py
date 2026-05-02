"""
NYU transcript parser.

Tries a deterministic regex pass first (fast, free, no PII leaves the
server). Falls back to a Gemini call only when the regex finds no
courses — e.g. unusual or non-undergraduate transcript formats.
"""
import json
import re
from typing import Any

from app.ai.client import client, MODEL


_COURSE_LINE_RE = re.compile(
    r'(?P<subject>[A-Z]{2,5}-[A-Z]{2,3})\s+'
    r'(?P<number>[0-9]+[A-Z]?)-'
    r'(?P<section>[0-9]+)\s+'
    r'(?P<credits>[0-9]+\.[0-9]+)\s+'
    r'(?P<grade>\*\*\*|[A-DF][+-]?|P|S|SX|CR|T|W|WX|WD|I|NG|MG|AU)'
    r'(?:\s|$)'
)
_TEST_CREDIT_LINE_RE = re.compile(
    r'^\s*(?P<test>[A-Z]+_[A-Z]+)\s+'
    r'(?P<component>.+?)\s+'
    r'(?P<units>[0-9]+(?:\.[0-9]+)?)\s*$'
)
_COMPLETED_GRADES = {
    'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-',
    'P', 'S', 'SX', 'CR', 'T',
}


def _format_credits(value: float) -> int | float:
    return int(value) if value == int(value) else value


def _coerce_credit_value(value: Any) -> int | float:
    try:
        return _format_credits(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _empty_parse_result() -> dict[str, Any]:
    return {
        "completed": [],
        "current": [],
        "course_credits": {},
        "test_credits": [],
        "test_credit_total": 0,
    }


def _total_test_credits(test_credits: list[dict[str, Any]]) -> int | float:
    total = sum(float(_coerce_credit_value(credit.get("units"))) for credit in test_credits)
    return _format_credits(total)


def _parse_test_credit_line(line: str) -> dict[str, Any] | None:
    match = _TEST_CREDIT_LINE_RE.search(line)
    if not match:
        return None
    units = _coerce_credit_value(match["units"])
    return {
        "test": match["test"],
        "component": " ".join(match["component"].split()),
        "units": units,
    }


def _coerce_parse_result(parsed: dict[str, Any]) -> dict[str, Any]:
    test_credits = parsed.get("test_credits") or []
    if not isinstance(test_credits, list):
        test_credits = []
    test_credit_total = parsed.get("test_credit_total")
    if test_credit_total is None:
        test_credit_total = _total_test_credits(test_credits)
    else:
        test_credit_total = _coerce_credit_value(test_credit_total)
    return {
        "completed": parsed.get("completed", []),
        "current": parsed.get("current", []),
        "course_credits": parsed.get("course_credits", {}),
        "test_credits": test_credits,
        "test_credit_total": test_credit_total,
    }


def _parse_transcript_regex(text: str) -> dict:
    """Deterministic NYU transcript parser. Returns empty lists if no matches.

    Excluded grades (W/I/AU/etc) are silently skipped without blocking a later
    valid attempt of the same course code from being counted — handles the
    withdraw-then-retake case correctly.
    """
    completed: list[str] = []
    current: list[str] = []
    credits_map: dict[str, Any] = {}
    test_credits: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in text.splitlines():
        test_credit = _parse_test_credit_line(line)
        if test_credit:
            test_credits.append(test_credit)
            continue
        if 'Test Credits' in line or 'Test Component' in line:
            continue
        m = _COURSE_LINE_RE.search(line)
        if not m:
            continue
        code = f"{m['subject']} {m['number']}"
        if code in seen:
            continue
        cr = _format_credits(float(m['credits']))
        grade = m['grade']
        if grade == '***':
            current.append(code)
            credits_map[code] = cr
            seen.add(code)
        elif grade in _COMPLETED_GRADES:
            completed.append(code)
            credits_map[code] = cr
            seen.add(code)
    return {
        "completed": completed,
        "current": current,
        "course_credits": credits_map,
        "test_credits": test_credits,
        "test_credit_total": _total_test_credits(test_credits),
    }


def _parse_transcript_ai(text: str) -> dict:
    """Gemini fallback parser. Used only when the regex parser finds nothing."""
    prompt = (
        "You are parsing an NYU student transcript. Scan the ENTIRE transcript carefully.\n\n"
        "Return a JSON object with exactly five keys:\n"
        "  \"completed\": list of course codes with a real grade (A+, A, A-, B+, B, B-, C+, C, C-, D+, D, D-, P, S, SX, CR, T)\n"
        "  \"current\": list of course codes marked with *** (currently enrolled, grade not yet posted)\n"
        "  \"course_credits\": object mapping each course code (from both completed and current) to its credit hours as a number\n"
        "  \"test_credits\": list of test/AP/IB credit entries as objects with test, component, and units\n"
        "  \"test_credit_total\": total units from test_credits as a number\n\n"
        "Exclude from completed and current: withdrawn (W, WX, WD), incomplete (I), no grade (NG, MG), audited (AU), "
        "and ALL test/AP/IB credits. Put entries under 'Test Credits' sections, or codes like ADV_PL, AP, IB, CLEP, "
        "only in test_credits.\n"
        "Use NYU course code format, e.g. \"CSCI-UA 101\". No duplicates.\n"
        "Return raw JSON only — no explanation, no markdown.\n\n"
        "Example output:\n"
        '{"completed": ["CSCI-UA 101", "MATH-UA 123"], "current": ["CSCI-UA 201"], '
        '"course_credits": {"CSCI-UA 101": 4, "MATH-UA 123": 4, "CSCI-UA 201": 4}, '
        '"test_credits": [{"test": "ADV_PL", "component": "Calculus BC", "units": 4}], '
        '"test_credit_total": 4}\n\n'
        f"Transcript text:\n{text}"
    )
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )
    raw = (response.text or "").strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            return _coerce_parse_result(parsed)
        except json.JSONDecodeError:
            pass
    return _empty_parse_result()


def parse_transcript(text: str) -> dict:
    """Try the regex parser first; fall back to Gemini if regex finds nothing."""
    parsed = _parse_transcript_regex(text)
    if parsed["completed"] or parsed["current"] or parsed["test_credits"]:
        return parsed
    return _parse_transcript_ai(text)
