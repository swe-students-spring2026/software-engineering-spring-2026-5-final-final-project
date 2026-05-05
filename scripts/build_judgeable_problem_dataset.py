"""Build CatCh's judgeable coding-problem dataset.

The LeetCode CSV is useful metadata, but it does not contain executable
tests or revealable answers. This script joins selected CSV rows with
curated judgeable overrides, then appends the existing Exercism seed
problems with known solutions.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
LEETCODE_CSV = REPO_ROOT / "data" / "leetcode_dataset - lc.csv"
LEETCODE_OVERRIDES = REPO_ROOT / "data" / "leetcode_judgeable_overrides.json"
EXERCISM_SEEDS = REPO_ROOT / "game-service" / "app" / "seeds" / "problems.json"
OUTPUT_PATH = REPO_ROOT / "data" / "judgeable_problems.json"

MAX_ATTEMPTS = 5

EXERCISM_SOLUTIONS = {
    "leap": (
        "def leap_year(year):\n"
        "    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)\n"
    ),
    "reverse-string": "def reverse(text):\n    return text[::-1]\n",
    "two-fer": (
        "def two_fer(name='you'):\n"
        "    return f'One for {name}, one for me.'\n"
    ),
    "isogram": (
        "def is_isogram(string):\n"
        "    letters = [char.lower() for char in string if char.isalpha()]\n"
        "    return len(letters) == len(set(letters))\n"
    ),
    "pangram": (
        "import string\n\n\n"
        "def is_pangram(sentence):\n"
        "    return set(string.ascii_lowercase).issubset(set(sentence.lower()))\n"
    ),
}


def fishing_reward_for_difficulty(difficulty: str) -> int:
    """Map problem difficulty to CatCh fishing reward."""

    return {
        "easy": 1,
        "medium": 2,
        "hard": 3,
    }.get(difficulty.lower(), 1)


def parse_float(value: str | None) -> float | None:
    """Parse a CSV numeric field, returning None when empty or malformed."""

    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def split_tags(value: str | None) -> list[str]:
    """Split comma-separated metadata into clean tags."""

    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def load_leetcode_rows() -> dict[str, dict[str, str]]:
    """Load LeetCode CSV rows by source id."""

    with LEETCODE_CSV.open(newline="", encoding="utf-8") as csv_file:
        return {row["id"]: row for row in csv.DictReader(csv_file)}


def build_leetcode_problem(
    row: dict[str, str],
    override: dict[str, Any],
) -> dict[str, Any]:
    """Combine a LeetCode metadata row with executable CatCh fields."""

    difficulty = row.get("difficulty", "Easy").lower()
    return {
        "id": f"leetcode-{row['id']}",
        "external_id": row["id"],
        "slug": override["slug"],
        "title": row["title"],
        "function_name": override["function_name"],
        "instructions": row["description"],
        "starter_code": override["starter_code"],
        "test_code": override["test_code"],
        "solution_code": override["solution_code"],
        "solution_explanation": override["solution_explanation"],
        "difficulty": difficulty,
        "fishing_reward": fishing_reward_for_difficulty(difficulty),
        "max_attempts": MAX_ATTEMPTS,
        "language": "python",
        "judgeable": True,
        "source": "LeetCode metadata with CatCh curated tests",
        "source_url": row.get("url") or f"https://leetcode.com/problems/{override['slug']}",
        "solution_url": (
            f"https://leetcode.com{row['solution_link']}"
            if row.get("solution_link")
            else None
        ),
        "acceptance_rate": parse_float(row.get("acceptance_rate")),
        "topics": split_tags(row.get("related_topics")),
        "companies": split_tags(row.get("companies")),
    }


def build_exercism_problem(entry: dict[str, Any]) -> dict[str, Any]:
    """Normalize an existing Exercism seed into the shared judgeable schema."""

    problem_id = entry["id"]
    return {
        **entry,
        "external_id": problem_id,
        "slug": problem_id,
        "solution_code": EXERCISM_SOLUTIONS.get(problem_id, ""),
        "solution_explanation": "Reference solution used after five failed attempts.",
        "max_attempts": MAX_ATTEMPTS,
        "language": "python",
        "judgeable": True,
        "topics": [],
        "companies": [],
    }


def build_dataset() -> list[dict[str, Any]]:
    """Build the combined dataset in deterministic order."""

    leetcode_rows = load_leetcode_rows()
    overrides = json.loads(LEETCODE_OVERRIDES.read_text(encoding="utf-8"))
    problems = []

    for override in overrides:
        row = leetcode_rows.get(str(override["leetcode_id"]))
        if row is None:
            raise ValueError(f"missing CSV row for LeetCode id {override['leetcode_id']}")
        problems.append(build_leetcode_problem(row, override))

    exercism_entries = json.loads(EXERCISM_SEEDS.read_text(encoding="utf-8"))
    problems.extend(build_exercism_problem(entry) for entry in exercism_entries)
    return problems


def main() -> None:
    """Write data/judgeable_problems.json."""

    problems = build_dataset()
    OUTPUT_PATH.write_text(
        json.dumps(problems, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(problems)} judgeable problems to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
