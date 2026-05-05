from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

DEFAULT_DATABASE_NAME = "meme_generator"
DEFAULT_COLLECTION_NAME = "generated_memes"


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


SAMPLE_MEMES: list[dict[str, Any]] = [
    {
        "person_name": "Milan",
        "source_url": "https://example.com/nyc-rent-article",
        "article_text": None,
        "article_summary": "Students read one article about New York rent prices and suddenly become housing experts.",
        "template": "drake",
        "top_text": "Ignoring the article",
        "bottom_text": "Explaining NYC rent like a pro",
        "meme_url": "https://api.memegen.link/images/drake/Ignoring_the_article/Explaining_NYC_rent_like_a_pro.jpg",
        "created_at": "2026-05-04T12:00:00+00:00",
    },
    {
        "person_name": "Ermuun",
        "source_url": None,
        "article_text": "Campus dining prices rose again, and students are pretending meal swipes are a luxury currency.",
        "article_summary": "Students complain about dining prices but still buy snacks between classes.",
        "template": "buzz",
        "top_text": "Reading one campus article",
        "bottom_text": "Acting like the dining hall CFO",
        "meme_url": "https://api.memegen.link/images/buzz/Reading_one_campus_article/Acting_like_the_dining_hall_CFO.jpg",
        "created_at": "2026-05-04T12:05:00+00:00",
    },
    {
        "person_name": "Yuliang",
        "source_url": "https://example.com/ai-on-campus",
        "article_text": None,
        "article_summary": "An article about AI tools on campus turns into a meme about students using chatbots for everything.",
        "template": "doge",
        "top_text": "Such research",
        "bottom_text": "Very article. Much meme.",
        "meme_url": "https://api.memegen.link/images/doge/Such_research/Very_article._Much_meme..jpg",
        "created_at": "2026-05-04T12:10:00+00:00",
    },
]


def build_generated_memes_seed() -> list[dict[str, Any]]:
    return deepcopy(SAMPLE_MEMES)


def build_runtime_seed() -> list[dict[str, Any]]:
    records = build_generated_memes_seed()
    now = _timestamp()
    for record in records:
        record["created_at"] = now
    return records
