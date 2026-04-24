from __future__ import annotations

from typing import Any

try:
    from apis.app.scrapers.bulletins import NYUBulletinScraper
except ModuleNotFoundError:
    from scrapers.bulletins import NYUBulletinScraper


class RequirementsService:
    """Application-facing wrapper around bulletin scraping logic."""

    def __init__(self, scraper: NYUBulletinScraper | None = None) -> None:
        self.scraper = scraper or NYUBulletinScraper()

    def list_undergraduate_programs(self) -> list[dict[str, Any]]:
        programs = self.scraper.collect_undergraduate_program_links()
        return [
            {
                "title": program.title,
                "url": program.url,
                "school": program.school,
                "award": program.award,
            }
            for program in programs
        ]

    def fetch_program_requirements(self, url: str) -> dict[str, Any]:
        return self.scraper.scrape_program(url)
