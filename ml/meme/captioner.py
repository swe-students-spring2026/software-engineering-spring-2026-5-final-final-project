from __future__ import annotations

import re
from dataclasses import dataclass

@dataclass(frozen=True)
class MemeCaption:
    top: str
    bottom: str

def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def shorten(text: str, limit: int = 48) -> str:
    clean = normalize_text(text)
    if len(clean) <= limit:
        return clean
    clipped = clean[: limit - 1].rsplit(" ", 1)[0].strip()
    if not clipped:
        clipped = clean[: limit - 1]
    return clipped + "…"

def heuristic_caption(text: str) -> MemeCaption:
    clean = normalize_text(text)
    if not clean:
        return MemeCaption(top="No article text", bottom="No meme today")

    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", clean) if part.strip()]
    if len(sentences) >= 2:
        return MemeCaption(
            top=shorten(sentences[0], 42),
            bottom=shorten(" ".join(sentences[1:]), 42),
        )

    words = clean.split()
    if len(words) <= 7:
        return MemeCaption(top=shorten(clean, 40), bottom="me acting informed")

    midpoint = max(3, len(words) // 2)
    return MemeCaption(
        top=shorten(" ".join(words[:midpoint]), 42),
        bottom=shorten(" ".join(words[midpoint:]), 42),
    )

def generate_caption(text: str, use_ai: bool = False) -> MemeCaption:
    return heuristic_caption(text)