from __future__ import annotations

import json
import os
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

def ai_caption(text: str) -> MemeCaption:
    from openai import OpenAI

    client = OpenAI()
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        temperature=0.9,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You write short meme captions for students. "
                    "Return valid JSON with keys top and bottom only."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Turn this article text or summary into a funny, clear meme caption. "
                    "Keep each line under 8 words.\n\n"
                    f"Input: {text}"
                ),
            },
        ],
    )
    payload = json.loads(response.choices[0].message.content)
    return MemeCaption(
        top=shorten(str(payload.get("top", "Reading the article")), 40),
        bottom=shorten(str(payload.get("bottom", "pretending I get it")), 40),
    )

def generate_caption(text: str, use_ai: bool = False) -> MemeCaption:
    if use_ai:
        try:
            return ai_caption(text)
        except Exception:
            return heuristic_caption(text)
    return heuristic_caption(text)