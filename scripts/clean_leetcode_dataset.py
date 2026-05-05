"""Clean the LeetCode CSV into CatCh problem metadata JSON.

This does not make every row judgeable. Rows become judgeable only when they
also have curated tests and solutions in `leetcode_judgeable_overrides.json`.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = REPO_ROOT / "data" / "leetcode_dataset - lc.csv"
OVERRIDES_PATH = REPO_ROOT / "data" / "leetcode_judgeable_overrides.json"
OUTPUT_PATH = REPO_ROOT / "data" / "leetcode_clean_100.json"


def slugify(title: str) -> str:
    """Return a URL-safe slug for a problem title."""

    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "problem"


def split_csv_list(value: str | None) -> list[str]:
    """Split comma-separated CSV values into clean strings."""

    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_float(value: str | None) -> float | None:
    """Parse float values that may be empty."""

    if value in {None, ""}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_intish(value: str | None) -> int | None:
    """Parse values like 123, 1.2K, or 3M into approximate integers."""

    if value in {None, ""}:
        return None
    text = value.strip().replace(",", "")
    multiplier = 1
    if text.endswith("K"):
        multiplier = 1_000
        text = text[:-1]
    elif text.endswith("M"):
        multiplier = 1_000_000
        text = text[:-1]
    try:
        return int(float(text) * multiplier)
    except ValueError:
        return None


def load_judgeable_ids() -> set[str]:
    """Return LeetCode ids that have curated executable overrides."""

    overrides = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    return {str(override["leetcode_id"]) for override in overrides}


def normalize_row(row: dict[str, str], judgeable_ids: set[str]) -> dict[str, Any]:
    """Normalize one CSV row into CatCh metadata."""

    leetcode_id = row["id"]
    slug = slugify(row["title"])
    return {
        "id": f"leetcode-{leetcode_id}",
        "external_id": leetcode_id,
        "slug": slug,
        "title": row["title"].strip(),
        "description": row["description"].strip(),
        "difficulty": row.get("difficulty", "").strip().lower(),
        "is_premium": row.get("is_premium") == "1",
        "source": "LeetCode metadata CSV",
        "source_url": row.get("url") or f"https://leetcode.com/problems/{slug}",
        "solution_url": (
            f"https://leetcode.com{row['solution_link']}"
            if row.get("solution_link")
            else None
        ),
        "topics": split_csv_list(row.get("related_topics")),
        "companies": split_csv_list(row.get("companies")),
        "stats": {
            "acceptance_rate": parse_float(row.get("acceptance_rate")),
            "frequency": parse_float(row.get("frequency")),
            "discuss_count": parse_intish(row.get("discuss_count")),
            "accepted": parse_intish(row.get("accepted")),
            "submissions": parse_intish(row.get("submissions")),
            "likes": parse_intish(row.get("likes")),
            "dislikes": parse_intish(row.get("dislikes")),
            "rating": parse_float(row.get("rating")),
            "asked_by_faang": row.get("asked_by_faang") == "1",
        },
        "similar_questions_raw": row.get("similar_questions") or "",
        "judgeable": leetcode_id in judgeable_ids,
        "judgeable_reason": (
            "curated tests and solution available"
            if leetcode_id in judgeable_ids
            else "metadata only; add starter_code, test_code, and solution_code"
        ),
    }


def clean(limit: int = 100) -> list[dict[str, Any]]:
    """Clean the first `limit` non-premium rows."""

    judgeable_ids = load_judgeable_ids()
    cleaned = []
    with SOURCE_CSV.open(newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            if row.get("is_premium") == "1":
                continue
            cleaned.append(normalize_row(row, judgeable_ids))
            if len(cleaned) >= limit:
                break
    return cleaned


def main() -> None:
    """Write the cleaned 100-row dataset."""

    cleaned = clean()
    OUTPUT_PATH.write_text(
        json.dumps(cleaned, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    judgeable_count = sum(1 for problem in cleaned if problem["judgeable"])
    print(
        f"Wrote {len(cleaned)} cleaned LeetCode rows to {OUTPUT_PATH} "
        f"({judgeable_count} judgeable)."
    )


if __name__ == "__main__":
    main()
