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
    return normalized in _INCOMPLETE_TOPIC_TITLES


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


def strip_leading_topic(description: object, topic: object) -> str:
    text = compact_text(description)
    remainder = topic_prefix_remainder(text, topic)
    return text if remainder is None else remainder


def normalize_topic_title_fields(doc: dict[str, Any]) -> dict[str, Any]:
    """Promote split Albert topic headers and remove duplicate topic descriptions."""
    title = compact_text(doc.get("title", ""))
    topic = compact_text(doc.get("topic", ""))
    description = compact_text(doc.get("description", ""))

    if should_promote_topic_to_title(title, topic, description):
        doc["title"] = title_with_topic(title, topic)
        doc["description"] = strip_leading_topic(description, topic)
    else:
        if "title" in doc:
            doc["title"] = title
        if "description" in doc:
            doc["description"] = description
    return doc
