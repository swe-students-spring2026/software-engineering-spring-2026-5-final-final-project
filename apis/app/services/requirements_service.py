from __future__ import annotations

from typing import Any

class RequirementsService:
    """Read program requirements from MongoDB for API responses."""

    def __init__(self, db: Any, collection_name: str = "program_requirements") -> None:
        self.collection = db[collection_name]

    def list_undergraduate_programs(self) -> list[dict[str, Any]]:
        cursor = self.collection.find(
            {},
            {
                "_id": 0,
                "title": 1,
                "url": 1,
                "school": 1,
                "award": 1,
                "source.bulletin_year": 1,
                "scraped_at": 1,
            },
        ).sort("title", 1)
        return list(cursor)

    def fetch_program_requirements(self, url: str) -> dict[str, Any]:
        program = self.collection.find_one({"url": url}, {"_id": 0})
        return program or {}
