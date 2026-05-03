from __future__ import annotations

import re
from typing import Any


_SPACE_RE = re.compile(r"\s+")
_INCOMPLETE_TOPIC_TITLES = {
    "colloquium",
    "seminar",
    "special topic",
    "special topics",
    "topic",
    "topics",
}
_COURSE_UNITS_RE = re.compile(
    r"^[A-Z]{2,5}-[A-Z]{2,3}\s+[A-Z0-9.]+[A-Z]?\s+\|\s*"
    r"\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?\s+units?$",
    re.I,
)
_METADATA_PREFIXES = (
    "school:",
    "term:",
    "class#:",
    "section:",
    "class status:",
    "grading:",
    "instruction mode:",
    "course location:",
    "session:",
    "component:",
    "notes:",
    "visit the bookstore",
)


def compact_text(value: object) -> str:
    return _SPACE_RE.sub(" ", str(value or "")).strip()


def topic_prefix_remainder(value: object, topic: object) -> str | None:
    text = compact_text(value)
    topic_text = compact_text(topic)
    if not text or not topic_text:
        return None

    text_folded = text.casefold()
    topic_folded = topic_text.casefold()
    if text_folded == topic_folded:
        return ""
    if not text_folded.startswith(topic_folded):
        return None

    after_topic = text[len(topic_text) :]
    if not after_topic or after_topic[0].isalnum():
        return None
    return after_topic.lstrip(" \t:-|").strip()


def title_expects_topic(title: object) -> bool:
    text = compact_text(title)
    if not text:
        return False
    if text.endswith(":"):
        return True
    normalized = text.rstrip(":").casefold()
    last_segment = normalized.rsplit(":", 1)[-1].strip()
    return normalized in _INCOMPLETE_TOPIC_TITLES or last_segment in _INCOMPLETE_TOPIC_TITLES


def should_promote_topic_to_title(title: object, topic: object, description: object = "") -> bool:
    return bool(
        compact_text(topic)
        and compact_text(title)
        and (title_expects_topic(title) or topic_prefix_remainder(description, topic) is not None)
    )


def title_with_topic(title: object, topic: object) -> str:
    title_text = compact_text(title)
    topic_text = compact_text(topic)
    if not title_text or not topic_text:
        return title_text
    if topic_text.casefold() in title_text.casefold():
        return title_text
    if title_text.endswith(":"):
        return f"{title_text} {topic_text}"
    return f"{title_text}: {topic_text}"


def title_with_topics(title: object, topics: list[object]) -> str:
    title_text = compact_text(title)
    topic_texts: list[str] = []
    seen: set[str] = set()
    for topic in topics:
        text = compact_text(topic)
        folded = text.casefold()
        if not text or folded in seen or folded in title_text.casefold():
            continue
        seen.add(folded)
        topic_texts.append(text)
    if not title_text or not topic_texts:
        return title_text
    joined = "; ".join(topic_texts)
    if title_text.endswith(":"):
        return f"{title_text} {joined}"
    return f"{title_text}: {joined}"


def strip_leading_topic(description: object, topic: object) -> str:
    text = compact_text(description)
    remainder = topic_prefix_remainder(text, topic)
    return text if remainder is None else remainder


def is_metadata_line(value: object) -> bool:
    lower = compact_text(value).casefold()
    return bool(lower and any(lower.startswith(prefix) for prefix in _METADATA_PREFIXES))


def is_units_line(value: object) -> bool:
    return bool(_COURSE_UNITS_RE.match(compact_text(value)))


def is_title_continuation_line(value: object) -> bool:
    text = compact_text(value)
    if not text or is_metadata_line(text) or is_units_line(text):
        return False
    if len(text) > 90:
        return False
    if re.search(r"[.!?][\"')\]]?$", text):
        return False
    return True


def topic_title_lines_from_source(doc: dict[str, Any]) -> tuple[str, list[str]]:
    source_row = (doc.get("source") or {}).get("raw_row", [])
    code = compact_text(doc.get("code", ""))
    if not isinstance(source_row, list) or not code:
        return "", []

    for index, line in enumerate(source_row):
        text = compact_text(line)
        if not text.startswith(code) or is_units_line(text):
            continue
        title = compact_text(text[len(code) :])
        if not title_expects_topic(title):
            return "", []

        continuations: list[str] = []
        for next_line in source_row[index + 1 :]:
            next_text = compact_text(next_line)
            if not next_text:
                continue
            if next_text.startswith(code) or is_metadata_line(next_text) or is_units_line(next_text):
                break
            if not is_title_continuation_line(next_text):
                break
            continuations.append(next_text)
        return title, continuations
    return "", []


def strip_leading_topic_lines(description: object, lines: list[object]) -> str:
    text = compact_text(description)
    if not text:
        return ""

    for start in range(len(lines)):
        candidate = compact_text(" ".join(compact_text(line) for line in lines[start:]))
        if candidate and text.casefold().startswith(candidate.casefold()):
            return text[len(candidate) :].lstrip(" \t:-|")
    return text


def normalize_topic_title_fields(doc: dict[str, Any]) -> dict[str, Any]:
    """Promote split Albert topic headers and remove duplicate topic descriptions."""
    title = compact_text(doc.get("title", ""))
    topic = compact_text(doc.get("topic", ""))
    description = compact_text(doc.get("description", ""))
    source_title, source_topic_lines = topic_title_lines_from_source(doc)

    if source_title and source_topic_lines:
        doc["title"] = title_with_topics(source_title, source_topic_lines)
        doc["description"] = strip_leading_topic_lines(description, source_topic_lines)
        return doc

    if should_promote_topic_to_title(title, topic, description):
        doc["title"] = title_with_topic(title, topic)
        doc["description"] = strip_leading_topic(description, topic)
    else:
        if "title" in doc:
            doc["title"] = title
        if "description" in doc:
            doc["description"] = description
    return doc
